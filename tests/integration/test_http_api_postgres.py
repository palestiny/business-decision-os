import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.api.app import create_app
from decision_os.application.commands.create_decision_case import (
    CreateDecisionCaseCommand,
    CreateDecisionCaseHandler,
)
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.ports.authority import Permission
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.reliability import (
    AuditEventModel,
    IdempotencyRecordModel,
    OutboxMessageModel,
)
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.repositories.reliability import (
    SQLAlchemyAuditRepository,
    SQLAlchemyIdempotencyRepository,
    SQLAlchemyOutboxRepository,
)
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


class AllowCreateCaseAuthorization:
    def require(self, *, permission, **kwargs):
        assert permission is Permission.CREATE_CASE


@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()


def test_create_case_http_replay_uses_real_postgres_reliability_boundary(session: Session) -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    session.add(TenantModel(id=tenant_id, name="api-integration-test"))
    session.commit()

    uow = SQLAlchemyUnitOfWork(session)
    boundary = CreateDecisionCaseReliabilityBoundary(
        uow=uow,
        handler=CreateDecisionCaseHandler(uow, AllowCreateCaseAuthorization()),
        idempotency=SQLAlchemyIdempotencyRepository(session),
        audit=SQLAlchemyAuditRepository(session),
        outbox=SQLAlchemyOutboxRepository(session),
    )

    principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)

    def principal_provider(request):
        return principal

    client = TestClient(
        create_app(
            create_case_boundary=boundary,
            principal_provider=principal_provider,
        )
    )

    headers = {"Idempotency-Key": "http-create-001"}
    payload = {
        "case_type": "PROJECT_MARGIN_RISK",
        "title": "HTTP margin risk",
    }

    first = client.post("/api/v1/decision-cases", headers=headers, json=payload)
    second = client.post("/api/v1/decision-cases", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"] == second.json()["data"]

    case_id = first.json()["data"]["id"]
    assert session.scalar(
        select(DecisionCaseModel).where(DecisionCaseModel.id == case_id)
    ) is not None

    assert session.scalar(
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.tenant_id == tenant_id,
            IdempotencyRecordModel.operation == "CreateDecisionCase",
            IdempotencyRecordModel.key == "http-create-001",
        )
    ).status == "COMPLETED"

    assert len(session.scalars(
        select(AuditEventModel).where(AuditEventModel.entity_id == case_id)
    ).all()) == 1
    assert len(session.scalars(
        select(OutboxMessageModel).where(OutboxMessageModel.aggregate_id == case_id)
    ).all()) == 1
    assert len(session.scalars(
        select(DecisionCaseModel).where(DecisionCaseModel.tenant_id == tenant_id)
    ).all()) == 1
