from datetime import datetime, timezone
import os
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, close_all_sessions, sessionmaker

from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.infrastructure.persistence.models.action import ActionModel
from decision_os.infrastructure.persistence.models.decision import DecisionModel
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.readers.decision_work_queue import SessionFactoryDecisionWorkQueueReader
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
    session.add(TenantModel(id=tenant_id, name=f"work-queue-{tenant_id}"))
    session.commit()


def seed_case(session: Session, tenant_id, case_id, status, title="Case"):
    now = datetime.now(timezone.utc)
    session.add(DecisionCaseModel(
        id=case_id, tenant_id=tenant_id, case_type="PROJECT_MARGIN_RISK",
        title=title, status=status, version=3, created_at=now, updated_at=now,
    ))
    session.commit()


def build_client(session: Session, tenant_id):
    principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=tenant_id)

    def principal_provider(request: Request):
        return principal

    request_session_factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    reader = SessionFactoryDecisionWorkQueueReader(request_session_factory)
    return TestClient(create_app(
        create_case_boundary=object(),
        decision_work_queue_reader=reader,
        principal_provider=principal_provider,
    ))


def test_work_queue_is_tenant_scoped_and_omits_approved_case_without_ready_action(session: Session):
    tenant_id, other_tenant = uuid4(), uuid4()
    review_case, approved_case, foreign_case = uuid4(), uuid4(), uuid4()
    seed_tenant(session, tenant_id)
    seed_tenant(session, other_tenant)
    seed_case(session, tenant_id, review_case, "AWAITING_DECISION", "Needs decision")
    seed_case(session, tenant_id, approved_case, "APPROVED", "No action yet")
    seed_case(session, other_tenant, foreign_case, "AWAITING_DECISION", "Foreign tenant")

    response = build_client(session, tenant_id).get("/api/v1/decision-work-queue")

    assert response.status_code == 200
    items = response.json()["data"]
    assert [item["case_id"] for item in items] == [str(review_case)]
    assert items[0]["attention_state"] == "MAKE_DECISION"
    assert items[0]["authoritative_version"] == 3


def test_work_queue_marks_execute_only_when_action_is_ready(session: Session):
    tenant_id, case_id, decision_id, actor_id = uuid4(), uuid4(), uuid4(), uuid4()
    seed_tenant(session, tenant_id)
    seed_case(session, tenant_id, case_id, "APPROVED", "Ready action")
    now = datetime.now(timezone.utc)
    session.add(DecisionModel(
        id=decision_id, case_id=case_id, status="APPROVED",
        rationale="Proceed", decided_by=actor_id, decided_at=now,
        authority_snapshot=None, created_at=now, approval_required=False,
    ))
    session.flush()
    session.add(ActionModel(
        id=uuid4(), tenant_id=tenant_id, case_id=case_id, decision_id=decision_id,
        action_type="INTERNAL_CAPACITY_REALLOCATION", parameters="{}",
        status="READY", version=1,
    ))
    session.commit()

    response = build_client(session, tenant_id).get("/api/v1/decision-work-queue")

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["case_id"] == str(case_id)
    assert items[0]["attention_state"] == "EXECUTE_ACTION"
    assert items[0]["decision_id"] == str(decision_id)
