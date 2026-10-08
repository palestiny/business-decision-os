import os
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from decision_os.application.api.runtime import build_runtime_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.ports.authority import Permission
from decision_os.infrastructure.persistence.models.tenant import TenantModel

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


class AllowCreateCase:
    def require(self, *, actor_id, tenant_id, permission, resource_id):
        assert permission is Permission.CREATE_CASE


def test_runtime_create_case_is_visible_in_tenant_work_queue():
    tenant_id, actor_id = uuid4(), uuid4()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    seed_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    try:
        with seed_factory() as session:
            session.add(TenantModel(id=tenant_id, name=f"runtime-{tenant_id}"))
            session.commit()

        principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)

        def principal_provider(request: Request):
            return principal

        app = build_runtime_app(
            database_url=DATABASE_URL,
            authorization=AllowCreateCase(),
            principal_provider=principal_provider,
        )
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/decision-cases",
                headers={"Idempotency-Key": f"runtime-create-{uuid4()}"},
                json={"case_type": "PROJECT_MARGIN_RISK", "title": "Runtime composition check"},
            )
            assert created.status_code == 201, created.text
            case_id = created.json()["data"]["id"]

            queue = client.get("/api/v1/decision-work-queue")
            assert queue.status_code == 200, queue.text
            matches = [item for item in queue.json()["data"] if item["case_id"] == case_id]
            assert len(matches) == 1
            assert matches[0]["attention_state"] == "REVIEW_CASE"
    finally:
        engine.dispose()
