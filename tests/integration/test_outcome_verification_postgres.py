import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.commands.create_expected_outcome import CreateExpectedOutcomeCommand, CreateExpectedOutcomeHandler
from decision_os.application.commands.record_actual_outcome import RecordActualOutcomeCommand, RecordActualOutcomeHandler
from decision_os.application.commands.verify_outcome import VerifyOutcomeCommand, VerifyOutcomeHandler
from decision_os.application.create_expected_outcome_reliability import CreateExpectedOutcomeReliabilityBoundary
from decision_os.application.record_actual_outcome_reliability import RecordActualOutcomeReliabilityBoundary
from decision_os.application.verify_outcome_reliability import VerifyOutcomeReliabilityBoundary
from decision_os.application.ports.authority import Permission
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand, CreateDecisionCaseHandler
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.outcome import ActualOutcomeModel, VerificationModel
from decision_os.infrastructure.persistence.models.reliability import AuditEventModel, IdempotencyRecordModel, OutboxMessageModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from decision_os.infrastructure.persistence.repositories.reliability import SQLAlchemyAuditRepository, SQLAlchemyIdempotencyRepository, SQLAlchemyOutboxRepository
from decision_os.domain.decision_case import CaseStatus


DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests")


@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()


class AllowOutcomeAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission in {Permission.CREATE_OUTCOME, Permission.VERIFY_OUTCOME}


def seed_case(session: Session):
    tenant_id = uuid4()
    actor_id = uuid4()
    case_id = uuid4()
    session.add(TenantModel(id=tenant_id, name="outcome-integration"))
    session.commit()

    case = __import__("decision_os.domain.decision_case", fromlist=["DecisionCase"]).DecisionCase(
        case_id, tenant_id, "PROJECT_MARGIN_RISK", "Outcome integration case", CaseStatus.OUTCOME_PENDING, 8
    )
    __import__("decision_os.infrastructure.persistence.repositories.decision_case", fromlist=["SQLAlchemyDecisionCaseRepository"]).SQLAlchemyDecisionCaseRepository(session).add(case)
    session.commit()
    return tenant_id, actor_id, case


def test_outcome_verification_replay_persists_truth_and_single_side_effects(session: Session):
    tenant_id, actor_id, case = seed_case(session)
    uow = SQLAlchemyUnitOfWork(session)
    auth = AllowOutcomeAuthorization()
    idem = SQLAlchemyIdempotencyRepository(session)
    audit = SQLAlchemyAuditRepository(session)
    outbox = SQLAlchemyOutboxRepository(session)

    expected_id, actual_id, verification_id = uuid4(), uuid4(), uuid4()
    expected_boundary = CreateExpectedOutcomeReliabilityBoundary(
        uow=uow, handler=CreateExpectedOutcomeHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox
    )
    expected = expected_boundary.execute(
        CreateExpectedOutcomeCommand(
            tenant_id=tenant_id, case_id=case.id, actor_id=actor_id, outcome_id=expected_id,
            metric="margin_percent", operator="GTE", target=10,
        ),
        idempotency_key="expected-001",
    )
    assert expected.target == 10

    actual_boundary = RecordActualOutcomeReliabilityBoundary(
        uow=uow, handler=RecordActualOutcomeHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox
    )
    actual = actual_boundary.execute(
        RecordActualOutcomeCommand(
            tenant_id=tenant_id, case_id=case.id, actor_id=actor_id, outcome_id=actual_id,
            expected_outcome_id=expected.id, observed_value=12,
        ),
        idempotency_key="actual-001",
    )
    assert actual.status.value == "OBSERVED"

    verify_boundary = VerifyOutcomeReliabilityBoundary(
        uow=uow, handler=VerifyOutcomeHandler(uow, auth), idempotency=idem, audit=audit, outbox=outbox
    )
    command = VerifyOutcomeCommand(
        tenant_id=tenant_id, case_id=case.id, actor_id=actor_id,
        verification_id=verification_id, actual_outcome_id=actual.id,
    )
    first = verify_boundary.execute(command, idempotency_key="verify-001")
    replay = verify_boundary.execute(command, idempotency_key="verify-001")

    assert first.status.value == "PASSED"
    assert replay.status.value == "PASSED"

    persisted_case = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id))
    assert persisted_case is not None
    assert persisted_case.status == "CLOSED"
    assert persisted_case.version == 10

    persisted_actual = session.scalar(select(ActualOutcomeModel).where(ActualOutcomeModel.id == actual.id))
    assert persisted_actual is not None
    assert persisted_actual.status == "VERIFIED"

    persisted_verification = session.scalar(select(VerificationModel).where(VerificationModel.id == verification_id))
    assert persisted_verification is not None
    assert persisted_verification.status == "PASSED"

    audit_rows = session.scalars(select(AuditEventModel).where(AuditEventModel.entity_id == verification_id, AuditEventModel.action == "VerifyOutcome")).all()
    assert len(audit_rows) == 1
    outbox_rows = session.scalars(select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == verification_id, OutboxMessageModel.topic == "decision.outcome-verified")).all()
    assert len(outbox_rows) == 1
    idem_row = session.scalar(select(IdempotencyRecordModel).where(IdempotencyRecordModel.tenant_id == tenant_id, IdempotencyRecordModel.operation == "VerifyOutcome", IdempotencyRecordModel.key == "verify-001"))
    assert idem_row is not None
    assert idem_row.status == "COMPLETED"
