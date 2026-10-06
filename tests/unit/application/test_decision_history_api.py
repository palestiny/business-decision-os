from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Request
from fastapi.testclient import TestClient

from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.ports.decision_memory import DecisionMemoryView


class FakeDecisionMemoryReader:
    def __init__(self, view):
        self.view = view

    def get(self, *, tenant_id, case_id):
        if self.view.tenant_id != tenant_id or self.view.case_id != case_id:
            return None
        return self.view


def test_decision_history_returns_coherent_verified_narrative_from_memory():
    tenant_id = uuid4()
    case_id = uuid4()
    decision_id = uuid4()
    view = DecisionMemoryView(
        tenant_id=tenant_id,
        case_id=case_id,
        case_type="PROJECT_MARGIN_RISK",
        case_title="Margin risk",
        case_status="CLOSED",
        decision_id=decision_id,
        decision_status="APPROVED",
        rationale="Protect margin",
        decided_by=uuid4(),
        selected_option_ids=(uuid4(),),
        approval_required=True,
        action_summary={"status": "COMPLETED"},
        outcome_summary={"actual": {"observed_value": 90000}},
        verification_summary={"status": "PASS"},
        source_ids={"evidence_ids": [str(uuid4())]},
        authoritative_version=11,
        notified_version=11,
        projected_version=11,
        projected_at=datetime.now(timezone.utc),
        state="CURRENT",
    )
    principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=tenant_id)

    def principal_provider(request: Request):
        return principal

    app = create_app(
        create_case_boundary=object(),
        decision_memory_reader=FakeDecisionMemoryReader(view),
        principal_provider=principal_provider,
    )

    response = TestClient(app).get(
        f"/api/v1/decision-cases/{case_id}/history"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["case"]["id"] == str(case_id)
    assert data["decision"]["id"] == str(decision_id)
    assert data["decision"]["status"] == "APPROVED"
    assert data["action"]["status"] == "COMPLETED"
    assert data["outcome"]["actual"]["observed_value"] == 90000
    assert data["verification"]["status"] == "PASS"
    assert data["projection"]["state"] == "CURRENT"


def test_decision_history_is_tenant_scoped():
    case_id = uuid4()
    stored_tenant = uuid4()
    requesting_tenant = uuid4()
    view = DecisionMemoryView(
        tenant_id=stored_tenant,
        case_id=case_id,
        case_type="PROJECT_MARGIN_RISK",
        case_title="Margin risk",
        case_status="CLOSED",
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
        authoritative_version=3,
        notified_version=3,
        projected_version=3,
        projected_at=datetime.now(timezone.utc),
        state="CURRENT",
    )
    principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=requesting_tenant)

    def principal_provider(request: Request):
        return principal

    app = create_app(
        create_case_boundary=object(),
        decision_memory_reader=FakeDecisionMemoryReader(view),
        principal_provider=principal_provider,
    )

    response = TestClient(app).get(
        f"/api/v1/decision-cases/{case_id}/history"
    )

    assert response.status_code == 404
