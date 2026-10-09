from datetime import datetime, timezone
import os
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, close_all_sessions, sessionmaker

from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal


class AllowAuthorization:
    def require(self, **kwargs):
        return None
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
        authorization=AllowAuthorization(),
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
    assert response.json()["next_cursor"] is None
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



def test_work_queue_cursor_pages_are_bounded_and_do_not_duplicate_cases(session: Session):
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)
    case_ids = [uuid4() for _ in range(5)]
    for case_id in case_ids:
        seed_case(session, tenant_id, case_id, "AWAITING_DECISION", f"Case {case_id}")
    client = build_client(session, tenant_id)

    first = client.get("/api/v1/decision-work-queue", params={"limit": 2})
    assert first.status_code == 200
    assert len(first.json()["data"]) == 2
    assert first.json()["next_cursor"]

    second = client.get("/api/v1/decision-work-queue", params={"limit": 2, "cursor": first.json()["next_cursor"]})
    assert second.status_code == 200
    assert len(second.json()["data"]) == 2

    third = client.get("/api/v1/decision-work-queue", params={"limit": 2, "cursor": second.json()["next_cursor"]})
    assert third.status_code == 200
    assert len(third.json()["data"]) == 1
    assert third.json()["next_cursor"] is None

    collected = [row["case_id"] for response in (first, second, third) for row in response.json()["data"]]
    assert len(collected) == len(set(collected)) == 5


def test_work_queue_filters_compose_and_reject_unknown_values(session: Session):
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)
    seed_case(session, tenant_id, uuid4(), "AWAITING_DECISION", "Decision case")
    seed_case(session, tenant_id, uuid4(), "TRIAGED", "Review case")
    client = build_client(session, tenant_id)

    filtered = client.get("/api/v1/decision-work-queue", params={
        "attention_state": "MAKE_DECISION", "case_type": "PROJECT_MARGIN_RISK", "limit": 10,
    })
    assert filtered.status_code == 200
    assert len(filtered.json()["data"]) == 1
    assert filtered.json()["data"][0]["attention_state"] == "MAKE_DECISION"

    invalid = client.get("/api/v1/decision-work-queue", params={"attention_state": "NOPE"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_work_queue_rejects_malformed_cursor_with_standard_error(session: Session):
    tenant_id = uuid4()
    seed_tenant(session, tenant_id)
    client = build_client(session, tenant_id)

    response = client.get("/api/v1/decision-work-queue", params={"cursor": "not-a-valid-cursor"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


def test_cursor_reuse_never_changes_authenticated_tenant_scope(session: Session):
    tenant_a, tenant_b = uuid4(), uuid4()
    seed_tenant(session, tenant_a)
    seed_tenant(session, tenant_b)
    seed_case(session, tenant_a, UUID(int=10), "AWAITING_DECISION", "Tenant A first")
    seed_case(session, tenant_a, UUID(int=20), "AWAITING_DECISION", "Tenant A second")
    tenant_b_first, tenant_b_second = UUID(int=30), UUID(int=40)
    seed_case(session, tenant_b, tenant_b_first, "AWAITING_DECISION", "Tenant B first")
    seed_case(session, tenant_b, tenant_b_second, "AWAITING_DECISION", "Tenant B second")

    page_a = build_client(session, tenant_a).get("/api/v1/decision-work-queue", params={"limit": 1})
    assert page_a.status_code == 200
    cursor = page_a.json()["next_cursor"]
    assert cursor

    page_b = build_client(session, tenant_b).get(
        "/api/v1/decision-work-queue", params={"limit": 10, "cursor": cursor},
    )
    assert page_b.status_code == 200
    returned_ids = {row["case_id"] for row in page_b.json()["data"]}
    assert returned_ids == {str(tenant_b_first), str(tenant_b_second)}
