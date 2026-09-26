import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.ports.audit import AuditEvent
from decision_os.application.ports.idempotency import IdempotencyConflict
from decision_os.application.ports.outbox import OutboxMessage
from decision_os.domain.decision import Decision, DecisionOption
from decision_os.domain.decision_case import DecisionCase
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.models.decision import DecisionOptionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.repositories.decision import SQLAlchemyDecisionRepository
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
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
    outbox.add(
        OutboxMessage(
            id=uuid4(),
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
