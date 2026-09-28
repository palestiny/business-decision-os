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
    assert set(body) == {"data"}
    assert body["data"]["status"] == "DETECTED"
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
