from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.ports.decision_memory import DecisionMemoryView


class FakeDecisionMemoryReader:
    def __init__(self, view=None):
        self.view = view

    def get(self, *, tenant_id, case_id):
        if self.view is None:
            return None
        if self.view.tenant_id != tenant_id or self.view.case_id != case_id:
            return None
        return self.view


def _client(reader):
    tenant_id = uuid4()
    principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=tenant_id)
    return TestClient(create_app(
        create_case_boundary=object(),
        decision_memory_reader=reader,
        principal_provider=lambda request: principal,
    )), tenant_id


def test_decision_memory_read_returns_projection_and_consistency_metadata():
    tenant_id = uuid4()
    case_id = uuid4()
    view = DecisionMemoryView(
        tenant_id=tenant_id,
        case_id=case_id,
        case_type="PROJECT_MARGIN_RISK",
        case_title="Margin risk",
        case_status="CLOSED",
        decision_id=uuid4(),
        decision_status="APPROVED",
        rationale="Protect margin",
        decided_by=uuid4(),
        selected_option_ids=(uuid4(),),
        approval_required=True,
        action_summary={"status": "COMPLETED"},
        outcome_summary={"actual": {"observed_value": 90}},
        verification_summary={"status": "PASS"},
        source_ids={"evidence_ids": []},
        authoritative_version=11,
        notified_version=11,
        projected_version=11,
        projected_at=datetime.now(timezone.utc),
        state="CURRENT",
    )
    reader = FakeDecisionMemoryReader(view)
    principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=tenant_id)
    app = create_app(
        create_case_boundary=object(),
        decision_memory_reader=reader,
        principal_provider=lambda request: principal,
    )

    response = TestClient(app).get(f"/api/v1/decision-cases/{case_id}/memory")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["case_id"] == str(case_id)
    assert data["decision"]["status"] == "APPROVED"
    assert data["projection"]["state"] == "CURRENT"
    assert data["projection"]["authoritative_version"] == 11
    assert data["projection"]["projected_version"] == 11


def test_decision_memory_read_is_tenant_scoped_and_returns_not_found():
    case_id = uuid4()
    stored_tenant = uuid4()
    requesting_tenant = uuid4()
    view = DecisionMemoryView(
        tenant_id=stored_tenant,
        case_id=case_id,
        case_type="PROJECT_MARGIN_RISK",
        case_title="Margin risk",
        case_status="OPEN",
        decision_id=None,
        decision_status=None,
        rationale=None,
        decided_by=None,
        selected_option_ids=(),
        approval_required=None,
        action_summary=None,
        outcome_summary=None,
        verification_summary=None,
        source_ids={},
        authoritative_version=2,
        notified_version=2,
        projected_version=2,
        projected_at=datetime.now(timezone.utc),
        state="CURRENT",
    )
    principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=requesting_tenant)
    app = create_app(
        create_case_boundary=object(),
        decision_memory_reader=FakeDecisionMemoryReader(view),
        principal_provider=lambda request: principal,
    )

    response = TestClient(app).get(f"/api/v1/decision-cases/{case_id}/memory")

    assert response.status_code == 404
