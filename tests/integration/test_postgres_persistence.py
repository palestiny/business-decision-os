import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from decision_os.domain.decision_case import DecisionCase
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.session import build_session_factory


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
    factory.close_all()


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
