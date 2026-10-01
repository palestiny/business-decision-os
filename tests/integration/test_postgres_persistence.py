import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.commands.create_decision_case import (
    CreateDecisionCaseCommand,
    CreateDecisionCaseHandler,
)
from decision_os.application.ports.audit import AuditEvent
from decision_os.application.ports.authority import Permission
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.application.commands.triage_case import TriageCaseCommand, TriageCaseHandler
from decision_os.application.commands.make_decision import MakeDecisionCommand, MakeDecisionHandler
from decision_os.application.make_decision_reliability import MakeDecisionReliabilityBoundary
from decision_os.application.ports.authority import ApprovalDecision, PolicyEvaluationUnavailable
from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.infrastructure.persistence.repositories.decision_option import SQLAlchemyDecisionOptionRepository
from decision_os.application.triage_reliability import TriageCaseReliabilityBoundary
from decision_os.application.ports.idempotency import IdempotencyConflict
from decision_os.application.ports.outbox import OutboxMessage
from decision_os.domain.decision import Decision, DecisionOption
from decision_os.domain.decision_case import DecisionCase
from decision_os.infrastructure.persistence.models.reliability import (
    AuditEventModel,
    IdempotencyRecordModel,
    OutboxMessageModel,
)
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.models.decision import DecisionOptionModel, DecisionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.evidence import AnalysisFindingModel, EvidenceModel
from decision_os.infrastructure.persistence.repositories.decision import SQLAlchemyDecisionRepository
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.repositories.reliability import (
    SQLAlchemyAuditRepository,
    SQLAlchemyIdempotencyRepository,
    SQLAlchemyOutboxRepository,
)


DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()


class AllowCreateCaseAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.CREATE_CASE


class AllowTriageCaseAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.TRIAGE_CASE


class AllowAwaitDecisionAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.AWAIT_DECISION


class AllowSubmitOptionsAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.SUBMIT_OPTIONS


class AllowStartAnalysisAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.START_ANALYSIS


class AllowMakeDecisionAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.MAKE_DECISION


class AllowApproveDecisionAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.APPROVE_DECISION


class AllowRejectDecisionAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.REJECT_DECISION


class RequireApprovalPolicy:
    def __init__(self, policy_id):
        self.policy_id = policy_id

    def evaluate(self, **kwargs):
        return ApprovalDecision(required=True, policy_ids=(self.policy_id,))


class FailingOutbox:
    def __init__(self, delegate):
        self._delegate = delegate

    def add(self, message):
        self._delegate.add(message)
        raise RuntimeError("forced outbox failure")


class FailingIdempotencyCompletion:
    def __init__(self, delegate):
        self._delegate = delegate

    def reserve(self, **kwargs):
        return self._delegate.reserve(**kwargs)

    def complete(self, **kwargs):
        self._delegate.complete(**kwargs)
        raise RuntimeError("forced reliability failure")


def seed_tenant(session: Session, tenant_id):
    session.add(TenantModel(id=tenant_id, name="integration-test"))
    session.commit()


def make_case(tenant_id):
    return DecisionCase.create(
        id=uuid4(),
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Integration test case",
    )


def test_decision_case_round_trip_and_tenant_isolation(session: Session) -> None:
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    seed_tenant(session, tenant_id)
    seed_tenant(session, other_tenant_id)

    case = make_case(tenant_id)
    repository = SQLAlchemyDecisionCaseRepository(session)
    repository.add(case)
    session.commit()

    loaded = repository.get(case.id, tenant_id)
    hidden = repository.get(case.id, other_tenant_id)

    assert loaded is not None
    assert loaded.id == case.id
    assert loaded.tenant_id == tenant_id
    assert loaded.status == case.status
    assert loaded.version == 0
    assert hidden is None


def test_decision_case_optimistic_concurrency_conflict(session: Session) -> None:
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    repository = SQLAlchemyDecisionCaseRepository(session)
    repository.add(case)
    session.commit()

    first = repository.get(case.id, tenant_id)
    second = repository.get(case.id, tenant_id)
    assert first is not None and second is not None

    first.triage()
    repository.save(first)
    session.commit()

    second.triage()
    with pytest.raises(RuntimeError, match="concurrency conflict"):
        repository.save(second)
    session.rollback()

    persisted = repository.get(case.id, tenant_id)
    assert persisted is not None
    assert persisted.version == 1


def test_rollback_does_not_persist_new_case(session: Session) -> None:
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    repository = SQLAlchemyDecisionCaseRepository(session)
    repository.add(case)
    session.rollback()

    assert session.scalar(
        select(DecisionCaseModel).where(DecisionCaseModel.id == case.id)
    ) is None


def test_decision_repository_round_trip_with_authority_snapshot(session: Session) -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    policy_ids = (uuid4(), uuid4())
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case_repository = SQLAlchemyDecisionCaseRepository(session)
    case_repository.add(case)
    session.flush()

    option = DecisionOption(id=uuid4(), case_id=case.id, title="Reduce scope")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    session.commit()

    decision = Decision.make(
        id=uuid4(), case_id=case.id, available_options=(option,), selected_option_ids=(option.id,),
        rationale="Protect delivery margin.", decided_by=user_id, approval_required=True,
        policy_ids=policy_ids,
    )
    repository = SQLAlchemyDecisionRepository(session)
    repository.add(decision)
    session.commit()

    loaded = repository.get(decision.id, tenant_id)

    assert loaded is not None
    assert loaded.approval_required is True
    assert loaded.policy_ids == policy_ids


def test_decision_repository_round_trip_with_selected_option(session: Session) -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case_repository = SQLAlchemyDecisionCaseRepository(session)
    case_repository.add(case)
    session.flush()

    option = DecisionOption(id=uuid4(), case_id=case.id, title="Reduce scope")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    session.commit()

    decision = Decision.make(
        id=uuid4(),
        case_id=case.id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Protect delivery margin.",
        decided_by=user_id,
        approval_required=True,
    )

    repository = SQLAlchemyDecisionRepository(session)
    repository.add(decision)
    session.commit()

    loaded = repository.get(decision.id, tenant_id)

    assert loaded is not None
    assert loaded.id == decision.id
    assert loaded.case_id == case.id
    assert loaded.selected_option_ids == (option.id,)
    assert loaded.rationale == decision.rationale
    assert loaded.approval_required is True
    assert loaded.status == decision.status


def test_decision_repository_persists_approval_and_rejection_status(session: Session) -> None:
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case_repository = SQLAlchemyDecisionCaseRepository(session)
    case_repository.add(case)
    session.flush()

    option = DecisionOption(id=uuid4(), case_id=case.id, title="Approve change")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    session.commit()

    repository = SQLAlchemyDecisionRepository(session)

    decision = Decision.make(
        id=uuid4(),
        case_id=case.id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Validated recovery path.",
        decided_by=uuid4(),
        approval_required=True,
    )
    repository.add(decision)
    session.commit()

    decision.approve()
    repository.save(decision, tenant_id)
    session.commit()

    approved = repository.get(decision.id, tenant_id)
    assert approved is not None
    assert approved.status == decision.status

    rejected_case = make_case(tenant_id)
    case_repository.add(rejected_case)
    session.flush()

    rejected_option = DecisionOption(id=uuid4(), case_id=rejected_case.id, title="Reject change")
    session.add(
        DecisionOptionModel(
            id=rejected_option.id,
            case_id=rejected_option.case_id,
            title=rejected_option.title,
        )
    )
    session.commit()

    rejected = Decision.make(
        id=uuid4(),
        case_id=rejected_case.id,
        available_options=(rejected_option,),
        selected_option_ids=(rejected_option.id,),
        rationale="Reject alternative.",
        decided_by=uuid4(),
        approval_required=True,
    )
    repository.add(rejected)
    session.commit()

    rejected.reject()
    repository.save(rejected, tenant_id)
    session.commit()

    persisted_rejected = repository.get(rejected.id, tenant_id)
    assert persisted_rejected is not None
    assert persisted_rejected.status == rejected.status


def test_create_case_reliability_boundary_persists_atomic_postgres_transaction(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    case_id = uuid4()
    seed_tenant(session, tenant_id)

    uow = SQLAlchemyUnitOfWork(session)
    idempotency = SQLAlchemyIdempotencyRepository(session)
    boundary = CreateDecisionCaseReliabilityBoundary(
        uow=uow,
        handler=CreateDecisionCaseHandler(uow, AllowCreateCaseAuthorization()),
        idempotency=idempotency,
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    command = CreateDecisionCaseCommand(
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Atomic PostgreSQL case",
        actor_id=actor_id,
        case_id=case_id,
    )

    case = boundary.execute(command, idempotency_key="atomic-success")
    assert case.id == case_id

    assert session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case_id)) is not None
    assert session.scalar(
        select(AuditEventModel).where(AuditEventModel.entity_id == case_id)
    ) is not None
    assert session.scalar(
        select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == case_id)
    ) is not None
    idempotency_row = session.scalar(
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.tenant_id == tenant_id,
            IdempotencyRecordModel.operation == "CreateDecisionCase",
            IdempotencyRecordModel.key == "atomic-success",
        )
    )
    assert idempotency_row is not None
    assert idempotency_row.status == "COMPLETED"


def test_create_case_reliability_boundary_rolls_back_all_postgres_writes_on_failure(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    case_id = uuid4()
    seed_tenant(session, tenant_id)

    uow = SQLAlchemyUnitOfWork(session)
    real_idempotency = SQLAlchemyIdempotencyRepository(session)
    boundary = CreateDecisionCaseReliabilityBoundary(
        uow=uow,
        handler=CreateDecisionCaseHandler(uow, AllowCreateCaseAuthorization()),
        idempotency=FailingIdempotencyCompletion(real_idempotency),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    command = CreateDecisionCaseCommand(
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Atomic PostgreSQL rollback",
        actor_id=actor_id,
        case_id=case_id,
    )

    with pytest.raises(RuntimeError, match="forced reliability failure"):
        boundary.execute(command, idempotency_key="atomic-failure")

    assert session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case_id)) is None
    assert session.scalar(
        select(AuditEventModel).where(AuditEventModel.entity_id == case_id)
    ) is None
    assert session.scalar(
        select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == case_id)
    ) is None
    assert session.scalar(
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.tenant_id == tenant_id,
            IdempotencyRecordModel.operation == "CreateDecisionCase",
            IdempotencyRecordModel.key == "atomic-failure",
        )
    ) is None


def test_idempotency_key_isolation_is_tenant_scoped(session: Session) -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    seed_tenant(session, tenant_a)
    seed_tenant(session, tenant_b)

    repository = SQLAlchemyIdempotencyRepository(session)
    first = repository.reserve(
        tenant_id=tenant_a,
        operation="CreateDecisionCase",
        key="shared-key",
        request_hash="hash-a",
    )
    second = repository.reserve(
        tenant_id=tenant_b,
        operation="CreateDecisionCase",
        key="shared-key",
        request_hash="hash-b",
    )

    assert first.tenant_id == tenant_a
    assert second.tenant_id == tenant_b
    assert first.key == second.key == "shared-key"
    assert first.status == second.status == "IN_PROGRESS"

    session.commit()

    rows = session.scalars(
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.operation == "CreateDecisionCase",
            IdempotencyRecordModel.key == "shared-key",
        )
    ).all()
    assert {row.tenant_id for row in rows} == {tenant_a, tenant_b}


def test_reliability_adapters_persist_in_one_transaction(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    seed_tenant(session, tenant_id)

    idempotency = SQLAlchemyIdempotencyRepository(session)
    audit = SQLAlchemyAuditRepository(session)
    outbox = SQLAlchemyOutboxRepository(session)

    record = idempotency.reserve(
        tenant_id=tenant_id,
        operation="CreateDecisionCase",
        key="integration-1",
        request_hash="hash-1",
    )
    assert record.status == "IN_PROGRESS"

    case_id = uuid4()
    now = datetime.now(timezone.utc)
    audit.append(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="CreateDecisionCase",
            entity_type="DecisionCase",
            entity_id=case_id,
            occurred_at=now,
            correlation_id=uuid4(),
        )
    )
    correlation_id = uuid4()
    outbox.add(
        OutboxMessage(
            id=uuid4(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            topic="decision-case.created",
            aggregate_type="DecisionCase",
            aggregate_id=case_id,
            payload='{"case_id": "' + str(case_id) + '"}',
            occurred_at=now,
        )
    )
    idempotency.complete(
        tenant_id=tenant_id,
        operation="CreateDecisionCase",
        key="integration-1",
        response_status=201,
        response_body='{"id": "' + str(case_id) + '"}',
    )
    session.commit()

    completed = idempotency.reserve(
        tenant_id=tenant_id,
        operation="CreateDecisionCase",
        key="integration-1",
        request_hash="hash-1",
    )
    assert completed.status == "COMPLETED"
    assert completed.response_status == 201
    assert str(case_id) in (completed.response_body or "")

    with pytest.raises(IdempotencyConflict):
        idempotency.reserve(
            tenant_id=tenant_id,
            operation="CreateDecisionCase",
            key="integration-1",
            request_hash="different-hash",
        )


def test_triage_case_reliability_boundary_persists_atomic_postgres_transaction(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    case_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case.id = case_id
    SQLAlchemyDecisionCaseRepository(session).add(case)
    evidence_id = uuid4()
    session.add(EvidenceModel(
        id=evidence_id, tenant_id=tenant_id, case_id=case.id, source="PSA",
        metric="gross_margin_percent", value="12.5", unit="percent", period="2026-09",
        captured_at=datetime.now(timezone.utc), confidence=0.95, snapshot="project-123:margin",
    ))
    session.add(AnalysisFindingModel(
        id=uuid4(), tenant_id=tenant_id, case_id=case.id, kind="INFERENCE",
        statement="Margin erosion is present.", confidence=0.8,
        evidence_ids=json.dumps([str(evidence_id)]),
    ))
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = TriageCaseReliabilityBoundary(
        uow=uow,
        handler=TriageCaseHandler(uow, AllowTriageCaseAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    command = TriageCaseCommand(tenant_id=tenant_id, case_id=case_id, actor_id=actor_id)

    result = boundary.execute(command, idempotency_key="triage-atomic-success")

    assert result.status.value == "TRIAGED"
    persisted = session.scalar(
        select(DecisionCaseModel).where(DecisionCaseModel.id == case_id)
    )
    assert persisted is not None
    assert persisted.status == "TRIAGED"
    assert persisted.version == 1
    assert session.scalar(
        select(AuditEventModel).where(AuditEventModel.entity_id == case_id)
    ) is not None
    assert session.scalar(
        select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == case_id)
    ) is not None
    idempotency_row = session.scalar(
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.tenant_id == tenant_id,
            IdempotencyRecordModel.operation == "TriageCase",
            IdempotencyRecordModel.key == "triage-atomic-success",
        )
    )
    assert idempotency_row is not None
    assert idempotency_row.status == "COMPLETED"


def test_triage_case_reliability_boundary_rolls_back_all_postgres_writes_on_failure(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    case_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case.id = case_id
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    real_outbox = SQLAlchemyOutboxRepository(session)
    boundary = TriageCaseReliabilityBoundary(
        uow=uow,
        handler=TriageCaseHandler(uow, AllowTriageCaseAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=FailingOutbox(real_outbox),
    )
    command = TriageCaseCommand(tenant_id=tenant_id, case_id=case_id, actor_id=actor_id)

    with pytest.raises(RuntimeError, match="forced outbox failure"):
        boundary.execute(command, idempotency_key="triage-atomic-failure")

    persisted = session.scalar(
        select(DecisionCaseModel).where(DecisionCaseModel.id == case_id)
    )
    assert persisted is not None
    assert persisted.status == "DETECTED"
    assert persisted.version == 0
    assert session.scalar(
        select(AuditEventModel).where(AuditEventModel.entity_id == case_id)
    ) is None
    assert session.scalar(
        select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == case_id)
    ) is None
    assert session.scalar(
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.tenant_id == tenant_id,
            IdempotencyRecordModel.operation == "TriageCase",
            IdempotencyRecordModel.key == "triage-atomic-failure",
        )
    ) is None


def test_triage_case_http_postgres_contract_and_replay(session: Session) -> None:
    from fastapi.testclient import TestClient

    from decision_os.application.api.app import create_app

    tenant_id = uuid4()
    actor_id = uuid4()
    case_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case.id = case_id
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    triage_boundary = TriageCaseReliabilityBoundary(
        uow=uow,
        handler=TriageCaseHandler(uow, AllowTriageCaseAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    create_boundary = CreateDecisionCaseReliabilityBoundary(
        uow=uow,
        handler=CreateDecisionCaseHandler(uow, AllowCreateCaseAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )

    app = create_app(
        create_case_boundary=create_boundary,
        triage_case_boundary=triage_boundary,
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        from decision_os.application.ports.authentication import AuthenticatedPrincipal

        request.state.principal = AuthenticatedPrincipal(
            actor_id=actor_id,
            tenant_id=tenant_id,
        )
        return await call_next(request)

    client = TestClient(app)
    headers = {"Idempotency-Key": "triage-http-001"}

    first = client.post(
        f"/api/v1/decision-cases/{case_id}/triage",
        headers=headers,
    )
    replay = client.post(
        f"/api/v1/decision-cases/{case_id}/triage",
        headers=headers,
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["data"]["status"] == "TRIAGED"
    assert first.json()["data"]["version"] == 1
    assert first.json()["correlation_id"] != replay.json()["correlation_id"]

    persisted = session.scalar(
        select(DecisionCaseModel).where(DecisionCaseModel.id == case_id)
    )
    assert persisted is not None
    assert persisted.status == "TRIAGED"
    assert persisted.version == 1

    audit_rows = session.scalars(
        select(AuditEventModel).where(
            AuditEventModel.entity_id == case_id,
            AuditEventModel.action == "TriageCase",
        )
    ).all()
    assert len(audit_rows) == 1

    outbox_rows = session.scalars(
        select(OutboxMessageModel).where(
            OutboxMessageModel.aggregate_id == case_id,
            OutboxMessageModel.topic == "decision-case.triaged",
        )
    ).all()
    assert len(outbox_rows) == 1

    idempotency_row = session.scalar(
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.tenant_id == tenant_id,
            IdempotencyRecordModel.operation == "TriageCase",
            IdempotencyRecordModel.key == "triage-http-001",
        )
    )
    assert idempotency_row is not None
    assert idempotency_row.status == "COMPLETED"



def test_start_analysis_http_postgres_replay_persists_transition_and_single_side_effects(session: Session) -> None:
    from fastapi.testclient import TestClient
    from decision_os.application.api.app import create_app
    from decision_os.application.commands.start_analysis import StartAnalysisHandler
    from decision_os.application.start_analysis_reliability import StartAnalysisReliabilityBoundary
    from decision_os.domain.decision_case import CaseStatus

    tenant_id = uuid4()
    actor_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case.status = CaseStatus.TRIAGED
    case.version = 1
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = StartAnalysisReliabilityBoundary(
        uow=uow,
        handler=StartAnalysisHandler(uow, AllowStartAnalysisAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    app = create_app(create_case_boundary=object(), start_analysis_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)
        return await call_next(request)

    client = TestClient(app)
    path = f"/api/v1/decision-cases/{case.id}/analysis/start"
    headers = {"Idempotency-Key": "analysis-http-001"}
    first = client.post(path, headers=headers)
    replay = client.post(path, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["data"]["status"] == "ANALYZING"
    assert first.json()["data"]["version"] == 2
    assert first.json()["correlation_id"] != replay.json()["correlation_id"]

    persisted = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id))
    assert persisted is not None
    assert persisted.status == "ANALYZING"
    assert persisted.version == 2

    audit_rows = session.scalars(select(AuditEventModel).where(
        AuditEventModel.entity_id == case.id,
        AuditEventModel.action == "StartAnalysis",
    )).all()
    assert len(audit_rows) == 1
    outbox_rows = session.scalars(select(OutboxMessageModel).where(
        OutboxMessageModel.aggregate_id == case.id,
        OutboxMessageModel.topic == "decision-case.analysis-started",
    )).all()
    assert len(outbox_rows) == 1

def test_make_decision_http_postgres_replay_persists_authority_and_single_side_effects(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    case = make_case(tenant_id)
    case.status = __import__("decision_os.domain.decision_case", fromlist=["CaseStatus"]).CaseStatus.AWAITING_DECISION
    case.version = 4
    seed_tenant(session, tenant_id)
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.flush()
    option = DecisionOption(id=uuid4(), case_id=case.id, title="Protect margin")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = MakeDecisionReliabilityBoundary(
        uow=uow,
        handler=MakeDecisionHandler(
            uow,
            AllowMakeDecisionAuthorization(),
            RequireApprovalPolicy(uuid4()),
        ),
        option_repository=SQLAlchemyDecisionOptionRepository(session),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )

    app = create_app(create_case_boundary=object(), make_decision_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)
        return await call_next(request)

    from fastapi.testclient import TestClient
    client = TestClient(app)
    decision_id = uuid4()
    payload = {
        "decision_id": str(decision_id),
        "option_ids": [str(option.id)],
        "rationale": "Protect delivery margin.",
    }
    first = client.post(
        f"/api/v1/decision-cases/{case.id}/decision",
        headers={"Idempotency-Key": "decision-http-001"},
        json=payload,
    )
    replay = client.post(
        f"/api/v1/decision-cases/{case.id}/decision",
        headers={"Idempotency-Key": "decision-http-001"},
        json=payload,
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["correlation_id"] != replay.json()["correlation_id"]
    assert first.json()["data"]["status"] == "AWAITING_APPROVAL"
    assert first.json()["data"]["approval_required"] is True

    persisted = SQLAlchemyDecisionRepository(session).get(decision_id, tenant_id)
    assert persisted is not None
    assert persisted.approval_required is True
    assert persisted.selected_option_ids == (option.id,)
    assert session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id)).status == "AWAITING_APPROVAL"
    assert session.scalar(select(AuditEventModel).where(AuditEventModel.entity_id == decision_id)) is not None
    assert len(session.scalars(select(AuditEventModel).where(AuditEventModel.entity_id == decision_id)).all()) == 1
    assert len(session.scalars(select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == decision_id)).all()) == 1
    idem = session.scalar(select(IdempotencyRecordModel).where(
        IdempotencyRecordModel.tenant_id == tenant_id,
        IdempotencyRecordModel.operation == "MakeDecision",
        IdempotencyRecordModel.key == "decision-http-001",
    ))
    assert idem is not None
    assert idem.status == "COMPLETED"


def test_make_decision_policy_unavailable_does_not_persist_postgres_state(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    case = make_case(tenant_id)
    case.status = __import__("decision_os.domain.decision_case", fromlist=["CaseStatus"]).CaseStatus.AWAITING_DECISION
    case.version = 1
    seed_tenant(session, tenant_id)
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.flush()
    option = DecisionOption(id=uuid4(), case_id=case.id, title="Protect margin")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    session.commit()

    class UnavailablePolicy:
        def evaluate(self, **kwargs):
            raise PolicyEvaluationUnavailable("temporarily unavailable")

    uow = SQLAlchemyUnitOfWork(session)
    boundary = MakeDecisionReliabilityBoundary(
        uow=uow,
        handler=MakeDecisionHandler(uow, AllowMakeDecisionAuthorization(), UnavailablePolicy()),
        option_repository=SQLAlchemyDecisionOptionRepository(session),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    with pytest.raises(PolicyEvaluationUnavailable):
        boundary.execute(
            MakeDecisionCommand(
                tenant_id=tenant_id, case_id=case.id, decision_id=uuid4(),
                option_ids=(option.id,), rationale="Protect margin.", actor_id=actor_id,
            ),
            idempotency_key="decision-policy-unavailable",
        )

    assert session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id)).status == "AWAITING_DECISION"
    assert session.scalars(select(DecisionModel).where(DecisionModel.case_id == case.id)).first() is None
    assert session.scalars(select(AuditEventModel).where(AuditEventModel.entity_id == case.id)).first() is None


def test_approve_decision_http_postgres_replay_persists_approval_and_single_side_effects(session: Session) -> None:
    from fastapi.testclient import TestClient
    from decision_os.domain.decision_case import CaseStatus
    from decision_os.application.approve_decision_reliability import ApproveDecisionReliabilityBoundary
    from decision_os.application.commands.approve_decision import ApproveDecisionHandler

    tenant_id = uuid4()
    actor_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case.status = CaseStatus.AWAITING_APPROVAL
    case.version = 2
    case_repository = SQLAlchemyDecisionCaseRepository(session)
    case_repository.add(case)
    session.flush()

    option = DecisionOption(id=uuid4(), case_id=case.id, title="Protect margin")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    session.flush()

    decision_id = uuid4()
    policy_id = uuid4()
    decision = Decision.make(
        id=decision_id,
        case_id=case.id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Protect delivery margin.",
        decided_by=uuid4(),
        approval_required=True,
        policy_ids=(policy_id,),
    )
    SQLAlchemyDecisionRepository(session).add(decision)
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = ApproveDecisionReliabilityBoundary(
        uow=uow,
        handler=ApproveDecisionHandler(uow, AllowApproveDecisionAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )

    app = create_app(create_case_boundary=object(), approve_decision_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)
        return await call_next(request)

    client = TestClient(app)
    path = f"/api/v1/decision-cases/{case.id}/decision/{decision_id}/approve"
    headers = {"Idempotency-Key": "approve-http-001"}
    first = client.post(path, headers=headers)
    replay = client.post(path, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["correlation_id"] != replay.json()["correlation_id"]
    assert first.json()["data"]["status"] == "APPROVED"

    persisted_decision = SQLAlchemyDecisionRepository(session).get(decision_id, tenant_id)
    assert persisted_decision is not None
    assert persisted_decision.status.value == "APPROVED"
    persisted_case = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id))
    assert persisted_case is not None
    assert persisted_case.status == "APPROVED"
    assert persisted_case.version == 3

    audit_rows = session.scalars(select(AuditEventModel).where(
        AuditEventModel.entity_id == decision_id,
        AuditEventModel.action == "ApproveDecision",
    )).all()
    assert len(audit_rows) == 1
    outbox_rows = session.scalars(select(OutboxMessageModel).where(
        OutboxMessageModel.aggregate_id == decision_id,
        OutboxMessageModel.topic == "decision.approved",
    )).all()
    assert len(outbox_rows) == 1
    idem = session.scalar(select(IdempotencyRecordModel).where(
        IdempotencyRecordModel.tenant_id == tenant_id,
        IdempotencyRecordModel.operation == "ApproveDecision",
        IdempotencyRecordModel.key == "approve-http-001",
    ))
    assert idem is not None
    assert idem.status == "COMPLETED"


def test_reject_decision_http_postgres_replay_persists_rejection_and_single_side_effects(session: Session) -> None:
    from fastapi.testclient import TestClient
    from decision_os.domain.decision_case import CaseStatus
    from decision_os.application.reject_decision_reliability import RejectDecisionReliabilityBoundary
    from decision_os.application.commands.reject_decision import RejectDecisionHandler

    tenant_id = uuid4()
    actor_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case.status = CaseStatus.AWAITING_APPROVAL
    case.version = 2
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.flush()

    option = DecisionOption(id=uuid4(), case_id=case.id, title="Protect margin")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    session.flush()

    decision_id = uuid4()
    policy_id = uuid4()
    decision = Decision.make(
        id=decision_id,
        case_id=case.id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Protect delivery margin.",
        decided_by=uuid4(),
        approval_required=True,
        policy_ids=(policy_id,),
    )
    SQLAlchemyDecisionRepository(session).add(decision)
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = RejectDecisionReliabilityBoundary(
        uow=uow,
        handler=RejectDecisionHandler(uow, AllowRejectDecisionAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )

    app = create_app(create_case_boundary=object(), reject_decision_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)
        return await call_next(request)

    client = TestClient(app)
    path = f"/api/v1/decision-cases/{case.id}/decision/{decision_id}/reject"
    headers = {"Idempotency-Key": "reject-http-001"}
    first = client.post(path, headers=headers)
    replay = client.post(path, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["correlation_id"] != replay.json()["correlation_id"]
    assert first.json()["data"]["status"] == "REJECTED"

    persisted_decision = SQLAlchemyDecisionRepository(session).get(decision_id, tenant_id)
    assert persisted_decision is not None
    assert persisted_decision.status.value == "REJECTED"
    persisted_case = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id))
    assert persisted_case is not None
    assert persisted_case.status == "REJECTED"
    assert persisted_case.version == 3

    audit_rows = session.scalars(select(AuditEventModel).where(
        AuditEventModel.entity_id == decision_id,
        AuditEventModel.action == "RejectDecision",
    )).all()
    assert len(audit_rows) == 1
    outbox_rows = session.scalars(select(OutboxMessageModel).where(
        OutboxMessageModel.aggregate_id == decision_id,
        OutboxMessageModel.topic == "decision.rejected",
    )).all()
    assert len(outbox_rows) == 1
    idem = session.scalar(select(IdempotencyRecordModel).where(
        IdempotencyRecordModel.tenant_id == tenant_id,
        IdempotencyRecordModel.operation == "RejectDecision",
        IdempotencyRecordModel.key == "reject-http-001",
    ))
    assert idem is not None
    assert idem.status == "COMPLETED"


def test_submit_options_http_postgres_replay_persists_options_and_single_side_effects(session: Session) -> None:
    from fastapi.testclient import TestClient
    from decision_os.application.api.app import create_app
    from decision_os.application.commands.submit_options import SubmitOptionsHandler
    from decision_os.application.submit_options_reliability import SubmitOptionsReliabilityBoundary
    from decision_os.domain.decision_case import CaseStatus

    tenant_id = uuid4()
    actor_id = uuid4()
    seed_tenant(session, tenant_id)

    case = make_case(tenant_id)
    case.status = CaseStatus.ANALYZING
    case.version = 2
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.flush()
    session.add(AnalysisFindingModel(
        id=uuid4(),
        tenant_id=tenant_id,
        case_id=case.id,
        kind="FACT",
        statement="Current gross margin is below the expected threshold.",
        confidence=0.99,
        evidence_ids=json.dumps([]),
    ))
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = SubmitOptionsReliabilityBoundary(
        uow=uow,
        handler=SubmitOptionsHandler(uow, AllowSubmitOptionsAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    app = create_app(create_case_boundary=object(), submit_options_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)
        return await call_next(request)

    client = TestClient(app)
    option_a, option_b = uuid4(), uuid4()
    payload = [
        {"id": str(option_a), "title": "Reduce scope"},
        {"id": str(option_b), "title": "Add delivery capacity"},
    ]
    path = f"/api/v1/decision-cases/{case.id}/options"
    headers = {"Idempotency-Key": "options-http-001"}
    first = client.post(path, json=payload, headers=headers)
    replay = client.post(path, json=payload, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["data"]["status"] == "OPTIONS_READY"
    assert first.json()["data"]["version"] == 3
    assert first.json()["correlation_id"] != replay.json()["correlation_id"]

    options = session.scalars(select(DecisionOptionModel).where(DecisionOptionModel.case_id == case.id)).all()
    assert len(options) == 2
    persisted = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id))
    assert persisted is not None
    assert persisted.status == "OPTIONS_READY"
    assert persisted.version == 3

    audit_rows = session.scalars(select(AuditEventModel).where(
        AuditEventModel.entity_id == case.id,
        AuditEventModel.action == "SubmitOptions",
    )).all()
    assert len(audit_rows) == 1
    outbox_rows = session.scalars(select(OutboxMessageModel).where(
        OutboxMessageModel.aggregate_id == case.id,
        OutboxMessageModel.topic == "decision-case.options-submitted",
    )).all()
    assert len(outbox_rows) == 1


def test_await_decision_http_postgres_replay_persists_transition_and_single_side_effects(session: Session) -> None:
    from fastapi.testclient import TestClient
    from decision_os.application.api.app import create_app
    from decision_os.application.await_decision_reliability import AwaitDecisionReliabilityBoundary
    from decision_os.application.commands.await_decision import AwaitDecisionHandler
    from decision_os.domain.decision_case import CaseStatus

    tenant_id = uuid4()
    actor_id = uuid4()
    seed_tenant(session, tenant_id)
    case = make_case(tenant_id)
    case.status = CaseStatus.OPTIONS_READY
    case.version = 3
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.flush()
    option = DecisionOptionModel(id=uuid4(), case_id=case.id, title="Reduce scope")
    session.add(option)
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = AwaitDecisionReliabilityBoundary(
        uow=uow,
        handler=AwaitDecisionHandler(uow, AllowAwaitDecisionAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )
    app = create_app(create_case_boundary=object(), await_decision_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)
        return await call_next(request)

    client = TestClient(app)
    path = f"/api/v1/decision-cases/{case.id}/decision/await"
    headers = {"Idempotency-Key": "await-decision-http-001"}
    first = client.post(path, headers=headers)
    replay = client.post(path, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["data"]["status"] == "AWAITING_DECISION"
    assert first.json()["data"]["version"] == 4
    assert first.json()["correlation_id"] != replay.json()["correlation_id"]

    persisted = session.scalar(select(DecisionCaseModel).where(DecisionCaseModel.id == case.id))
    assert persisted is not None
    assert persisted.status == "AWAITING_DECISION"
    assert persisted.version == 4
    audit_rows = session.scalars(select(AuditEventModel).where(
        AuditEventModel.entity_id == case.id,
        AuditEventModel.action == "AwaitDecision",
    )).all()
    assert len(audit_rows) == 1
    outbox_rows = session.scalars(select(OutboxMessageModel).where(
        OutboxMessageModel.aggregate_id == case.id,
        OutboxMessageModel.topic == "decision-case.awaiting-decision",
    )).all()
    assert len(outbox_rows) == 1
