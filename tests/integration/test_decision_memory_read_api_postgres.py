from datetime import datetime, timezone
import os
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal


class AllowAuthorization:
    def require(self, **kwargs):
        return None
from decision_os.domain.decision_case import DecisionCase
from decision_os.infrastructure.persistence.models.decision_memory import DecisionMemoryProjectionModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.repositories.decision_memory import SQLAlchemyDecisionMemoryRepository
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
    close_all_sessions()


def seed_tenant(session: Session, tenant_id):
    session.add(TenantModel(id=tenant_id, name="decision-memory-api-test"))
    session.commit()


def seed_case(session: Session, tenant_id, case_id):
    case = DecisionCase.create(
        id=case_id,
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Margin risk",
    )
    case.version = 11
    SQLAlchemyDecisionCaseRepository(session).add(case)
    session.commit()


def seed_projection(session: Session, tenant_id, case_id):
    session.add(
        DecisionMemoryProjectionModel(
            id=uuid4(),
            tenant_id=tenant_id,
            case_id=case_id,
            case_type="PROJECT_MARGIN_RISK",
            case_title="Margin risk",
            case_status="CLOSED",
            decision_status="APPROVED",
            rationale="Protect margin",
            selected_option_ids=[],
            approval_required=True,
            action_summary={"status": "COMPLETED"},
            outcome_summary={"actual": {"observed_value": 90}},
            verification_summary={"status": "PASS"},
            source_ids={"evidence_ids": []},
            authoritative_version=11,
            notified_version=11,
            projected_version=11,
            projected_at=datetime.now(timezone.utc),
            last_projection_state="CURRENT",
        )
    )
    session.commit()


def build_client(session: Session, tenant_id):
    principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=tenant_id)
    reader = SQLAlchemyDecisionMemoryRepository(session)

    def principal_provider(request: Request):
        return principal

    return TestClient(
        create_app(
            create_case_boundary=object(),
        authorization=AllowAuthorization(),
            decision_memory_reader=reader,
            principal_provider=principal_provider,
        )
    )


def test_decision_memory_read_api_uses_real_postgres_reader(session: Session):
    tenant_id = uuid4()
    case_id = uuid4()
    seed_tenant(session, tenant_id)
    seed_case(session, tenant_id, case_id)
    seed_projection(session, tenant_id, case_id)

    response = build_client(session, tenant_id).get(
        f"/api/v1/decision-cases/{case_id}/memory"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["case_id"] == str(case_id)
    assert data["tenant_id"] == str(tenant_id)
    assert data["case_type"] == "PROJECT_MARGIN_RISK"
    assert data["decision"]["status"] == "APPROVED"
    assert data["projection"]["state"] == "CURRENT"
    assert data["projection"]["authoritative_version"] == 11
    assert data["projection"]["projected_version"] == 11


def test_decision_memory_read_api_enforces_tenant_isolation(session: Session):
    stored_tenant = uuid4()
    requesting_tenant = uuid4()
    case_id = uuid4()
    seed_tenant(session, stored_tenant)
    seed_tenant(session, requesting_tenant)
    seed_case(session, stored_tenant, case_id)
    seed_projection(session, stored_tenant, case_id)

    response = build_client(session, requesting_tenant).get(
        f"/api/v1/decision-cases/{case_id}/memory"
    )

    assert response.status_code == 404


def test_decision_history_api_uses_real_postgres_reader(session: Session):
    tenant_id = uuid4()
    case_id = uuid4()
    seed_tenant(session, tenant_id)
    seed_case(session, tenant_id, case_id)
    seed_projection(session, tenant_id, case_id)

    response = build_client(session, tenant_id).get(
        f"/api/v1/decision-cases/{case_id}/history"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["case"]["id"] == str(case_id)
    assert data["case"]["type"] == "PROJECT_MARGIN_RISK"
    assert data["case"]["status"] == "CLOSED"
    assert data["decision"]["status"] == "APPROVED"
    assert data["action"]["status"] == "COMPLETED"
    assert data["outcome"]["actual"]["observed_value"] == 90
    assert data["verification"]["status"] == "PASS"
    assert data["projection"]["state"] == "CURRENT"


def test_decision_history_api_enforces_tenant_isolation(session: Session):
    stored_tenant = uuid4()
    requesting_tenant = uuid4()
    case_id = uuid4()
    seed_tenant(session, stored_tenant)
    seed_tenant(session, requesting_tenant)
    seed_case(session, stored_tenant, case_id)
    seed_projection(session, stored_tenant, case_id)

    response = build_client(session, requesting_tenant).get(
        f"/api/v1/decision-cases/{case_id}/history"
    )

    assert response.status_code == 404
