from uuid import uuid4

from fastapi.testclient import TestClient

from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal, AuthenticationRequired
from decision_os.application.ports.authority import AuthorizationDenied
from decision_os.application.ports.idempotency import IdempotencyConflict, RequestInProgress
from decision_os.domain.decision_case import CaseStatus


class Boundary:
    def __init__(self):
        self.calls = []

    def execute(self, command, *, idempotency_key, correlation_id=None):
        self.calls.append((command, idempotency_key))
        from decision_os.domain.decision_case import DecisionCase
        return DecisionCase(
            id=command.case_id or uuid4(),
            tenant_id=command.tenant_id,
            case_type=command.case_type,
            title=command.title,
            status=CaseStatus.DETECTED,
            version=0,
        )


def client_with(boundary):
    app = create_app(create_case_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        return await call_next(request)

    return TestClient(app)


def test_create_case_maps_authenticated_identity_and_returns_stable_response():
    boundary = Boundary()
    client = client_with(boundary)
    response = client.post(
        "/api/v1/decision-cases",
        headers={"Idempotency-Key": "create-001"},
        json={"case_type": "PROJECT_MARGIN_RISK", "title": "Margin risk"},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"data", "correlation_id"}
    assert body["data"]["status"] == "DETECTED"
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]
    assert body["data"]["case_type"] == "PROJECT_MARGIN_RISK"
    assert boundary.calls[0][1] == "create-001"


def test_create_case_requires_idempotency_key():
    client = client_with(Boundary())
    response = client.post(
        "/api/v1/decision-cases",
        json={"case_type": "PROJECT_MARGIN_RISK", "title": "Margin risk"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["correlation_id"]


def test_create_case_requires_authentication():
    app = create_app(create_case_boundary=Boundary())
    client = TestClient(app)
    response = client.post(
        "/api/v1/decision-cases",
        headers={"Idempotency-Key": "create-002"},
        json={"case_type": "PROJECT_MARGIN_RISK", "title": "Margin risk"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_correlation_id_is_generated_and_returned():
    client = client_with(Boundary())
    response = client.post(
        "/api/v1/decision-cases",
        headers={
            "Idempotency-Key": "create-003",
            "X-Correlation-ID": str(uuid4()),
        },
        json={"case_type": "PROJECT_MARGIN_RISK", "title": "Margin risk"},
    )

    assert response.status_code == 201
    assert response.headers["X-Correlation-ID"]


def test_triage_case_uses_authenticated_identity_and_stable_response():
    from decision_os.domain.decision_case import DecisionCase

    class TriageBoundary:
        def __init__(self):
            self.calls = []

        def execute(self, command, *, idempotency_key, correlation_id=None):
            self.calls.append((command, idempotency_key, correlation_id))
            return DecisionCase(
                id=command.case_id,
                tenant_id=command.tenant_id,
                case_type="PROJECT_MARGIN_RISK",
                title="Margin risk",
                status=CaseStatus.TRIAGED,
                version=1,
            )

    create_boundary = Boundary()
    triage_boundary = TriageBoundary()
    app = create_app(
        create_case_boundary=create_boundary,
        triage_case_boundary=triage_boundary,
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        return await call_next(request)

    client = TestClient(app)
    case_id = uuid4()
    response = client.post(
        f"/api/v1/decision-cases/{case_id}/triage",
        headers={"Idempotency-Key": "triage-001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "correlation_id"}
    assert body["data"]["id"] == str(case_id)
    assert body["data"]["status"] == "TRIAGED"
    assert body["data"]["version"] == 1
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]
    assert triage_boundary.calls[0][0].case_id == case_id
    assert triage_boundary.calls[0][1] == "triage-001"


def test_triage_case_requires_idempotency_key():
    class TriageBoundary:
        def execute(self, *args, **kwargs):
            raise AssertionError("boundary must not run")

    app = create_app(
        create_case_boundary=Boundary(),
        triage_case_boundary=TriageBoundary(),
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    response = TestClient(app).post(
        f"/api/v1/decision-cases/{uuid4()}/triage",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_make_decision_uses_authenticated_identity_and_stable_response():
    from decision_os.domain.decision import Decision, DecisionStatus

    class MakeDecisionBoundary:
        def __init__(self):
            self.calls = []

        def execute(self, command, *, idempotency_key, correlation_id=None):
            self.calls.append((command, idempotency_key, correlation_id))
            return Decision(
                id=command.decision_id,
                case_id=command.case_id,
                selected_option_ids=command.option_ids,
                rationale=command.rationale,
                status=DecisionStatus.AWAITING_APPROVAL,
                decided_by=command.actor_id,
                _approval_required=True,
                policy_ids=(uuid4(),),
            )

    boundary = MakeDecisionBoundary()
    app = create_app(
        create_case_boundary=Boundary(),
        make_decision_boundary=boundary,
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        return await call_next(request)

    case_id = uuid4()
    decision_id = uuid4()
    option_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/decision-cases/{case_id}/decision",
        headers={"Idempotency-Key": "decision-001"},
        json={
            "decision_id": str(decision_id),
            "option_ids": [str(option_id)],
            "rationale": "Protect project margin.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "correlation_id"}
    assert body["data"]["id"] == str(decision_id)
    assert body["data"]["case_id"] == str(case_id)
    assert body["data"]["selected_option_ids"] == [str(option_id)]
    assert body["data"]["status"] == "AWAITING_APPROVAL"
    assert body["data"]["approval_required"] is True
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]
    assert boundary.calls[0][1] == "decision-001"


def test_make_decision_requires_idempotency_key():
    class MakeDecisionBoundary:
        def execute(self, *args, **kwargs):
            raise AssertionError("boundary must not run")

    app = create_app(
        create_case_boundary=Boundary(),
        make_decision_boundary=MakeDecisionBoundary(),
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    response = TestClient(app).post(
        f"/api/v1/decision-cases/{uuid4()}/decision",
        json={
            "decision_id": str(uuid4()),
            "option_ids": [str(uuid4())],
            "rationale": "Protect project margin.",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_approve_decision_uses_authenticated_identity_and_stable_response():
    from decision_os.domain.decision import Decision, DecisionStatus

    class ApproveDecisionBoundary:
        def __init__(self):
            self.calls = []

        def execute(self, command, *, idempotency_key, correlation_id=None):
            self.calls.append((command, idempotency_key, correlation_id))
            return Decision(
                id=command.decision_id,
                case_id=command.case_id,
                selected_option_ids=(uuid4(),),
                rationale="Protect project margin.",
                status=DecisionStatus.APPROVED,
                decided_by=uuid4(),
                _approval_required=True,
                policy_ids=(uuid4(),),
            )

    boundary = ApproveDecisionBoundary()
    app = create_app(
        create_case_boundary=Boundary(),
        approve_decision_boundary=boundary,
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    case_id = uuid4()
    decision_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/decision-cases/{case_id}/decision/{decision_id}/approve",
        headers={"Idempotency-Key": "approve-001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "correlation_id"}
    assert body["data"]["id"] == str(decision_id)
    assert body["data"]["case_id"] == str(case_id)
    assert body["data"]["status"] == "APPROVED"
    assert body["data"]["approval_required"] is True
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]
    assert boundary.calls[0][1] == "approve-001"


def test_approve_decision_requires_idempotency_key():
    class ApproveDecisionBoundary:
        def execute(self, *args, **kwargs):
            raise AssertionError("boundary must not run")

    app = create_app(
        create_case_boundary=Boundary(),
        approve_decision_boundary=ApproveDecisionBoundary(),
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    response = TestClient(app).post(
        f"/api/v1/decision-cases/{uuid4()}/decision/{uuid4()}/approve",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reject_decision_uses_authenticated_identity_and_stable_response():
    from decision_os.domain.decision import Decision, DecisionStatus

    class RejectDecisionBoundary:
        def __init__(self):
            self.calls = []

        def execute(self, command, *, idempotency_key, correlation_id=None):
            self.calls.append((command, idempotency_key, correlation_id))
            return Decision(
                id=command.decision_id,
                case_id=command.case_id,
                selected_option_ids=(uuid4(),),
                rationale="Rejected by authority.",
                status=DecisionStatus.REJECTED,
                decided_by=uuid4(),
                _approval_required=True,
                policy_ids=(uuid4(),),
            )

    boundary = RejectDecisionBoundary()
    app = create_app(
        create_case_boundary=Boundary(),
        reject_decision_boundary=boundary,
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    case_id = uuid4()
    decision_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/decision-cases/{case_id}/decision/{decision_id}/reject",
        headers={"Idempotency-Key": "reject-001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "correlation_id"}
    assert body["data"]["id"] == str(decision_id)
    assert body["data"]["case_id"] == str(case_id)
    assert body["data"]["status"] == "REJECTED"
    assert body["data"]["approval_required"] is True
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]
    assert boundary.calls[0][1] == "reject-001"


def test_reject_decision_requires_idempotency_key():
    class RejectDecisionBoundary:
        def execute(self, *args, **kwargs):
            raise AssertionError("boundary must not run")

    app = create_app(
        create_case_boundary=Boundary(),
        reject_decision_boundary=RejectDecisionBoundary(),
    )

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    response = TestClient(app).post(
        f"/api/v1/decision-cases/{uuid4()}/decision/{uuid4()}/reject",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_start_analysis_uses_authenticated_identity_and_stable_response():
    class StartAnalysisBoundary:
        def __init__(self):
            self.calls = []

        def execute(self, command, *, idempotency_key, correlation_id=None):
            self.calls.append((command, idempotency_key, correlation_id))
            return type("Case", (), {
                "id": command.case_id,
                "tenant_id": command.tenant_id,
                "case_type": "PROJECT_MARGIN_RISK",
                "title": "Margin risk",
                "status": type("Status", (), {"value": "ANALYZING"})(),
                "version": 2,
            })()

    boundary = StartAnalysisBoundary()
    app = create_app(create_case_boundary=Boundary(), start_analysis_boundary=boundary)

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    case_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/decision-cases/{case_id}/analysis/start",
        headers={"Idempotency-Key": "analysis-001"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(case_id)
    assert response.json()["data"]["status"] == "ANALYZING"
    assert response.json()["data"]["version"] == 2
    assert boundary.calls[0][1] == "analysis-001"


def test_start_analysis_requires_idempotency_key():
    class StartAnalysisBoundary:
        def execute(self, *args, **kwargs):
            raise AssertionError("boundary must not run")

    app = create_app(create_case_boundary=Boundary(), start_analysis_boundary=StartAnalysisBoundary())

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    response = TestClient(app).post(f"/api/v1/decision-cases/{uuid4()}/analysis/start")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
