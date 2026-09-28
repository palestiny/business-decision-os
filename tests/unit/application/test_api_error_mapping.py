from uuid import uuid4

from fastapi.testclient import TestClient

from decision_os.application.api.app import create_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.ports.authority import AuthorizationDenied
from decision_os.application.ports.idempotency import IdempotencyConflict, RequestInProgress


class RaisingBoundary:
    def __init__(self, exc):
        self.exc = exc

    def execute(self, *args, **kwargs):
        raise self.exc


def authenticated_client(exc):
    app = create_app(create_case_boundary=RaisingBoundary(exc))

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=uuid4())
        return await call_next(request)

    return TestClient(app)


def test_authorization_denied_maps_to_403():
    response = authenticated_client(AuthorizationDenied()).post(
        "/api/v1/decision-cases",
        headers={"Idempotency-Key": "k"},
        json={"case_type": "PROJECT_MARGIN_RISK", "title": "x"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"


def test_idempotency_conflict_maps_to_409():
    response = authenticated_client(IdempotencyConflict()).post(
        "/api/v1/decision-cases",
        headers={"Idempotency-Key": "k"},
        json={"case_type": "PROJECT_MARGIN_RISK", "title": "x"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_request_in_progress_maps_to_409():
    response = authenticated_client(RequestInProgress()).post(
        "/api/v1/decision-cases",
        headers={"Idempotency-Key": "k"},
        json={"case_type": "PROJECT_MARGIN_RISK", "title": "x"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REQUEST_IN_PROGRESS"
