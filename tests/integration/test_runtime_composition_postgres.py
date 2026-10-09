import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from decision_os.application.api.runtime import build_runtime_app
from decision_os.application.ports.authentication import AuthenticatedPrincipal
from decision_os.application.ports.authority import Permission
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


class AllowCreateCase:
    def require(self, *, actor_id, tenant_id, permission, resource_id, correlation_id=None):
        assert permission in {Permission.CREATE_CASE, Permission.TRIAGE_CASE, Permission.VIEW_DECISION_WORK_QUEUE}


def test_runtime_create_case_is_visible_in_tenant_work_queue():
    tenant_id, actor_id, other_tenant_id, other_actor_id = uuid4(), uuid4(), uuid4(), uuid4()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    seed_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    try:
        with seed_factory() as session:
            session.add_all([
                TenantModel(id=tenant_id, name=f"runtime-{tenant_id}"),
                TenantModel(id=other_tenant_id, name=f"runtime-{other_tenant_id}"),
            ])
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

        other_principal = AuthenticatedPrincipal(actor_id=other_actor_id, tenant_id=other_tenant_id)

        def other_principal_provider(request: Request):
            return other_principal

        other_app = build_runtime_app(
            database_url=DATABASE_URL,
            authorization=AllowCreateCase(),
            principal_provider=other_principal_provider,
        )
        with TestClient(other_app) as other_client:
            other_queue = other_client.get("/api/v1/decision-work-queue")
            assert other_queue.status_code == 200, other_queue.text
            assert all(item["case_id"] != case_id for item in other_queue.json()["data"])
    finally:
        engine.dispose()



def test_runtime_rolls_back_case_when_outbox_write_fails(monkeypatch):
    from decision_os.infrastructure.persistence.repositories.reliability import SQLAlchemyOutboxRepository

    tenant_id, actor_id = uuid4(), uuid4()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    seed_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    title = f"Rollback verification {uuid4()}"

    try:
        with seed_factory() as session:
            session.add(TenantModel(id=tenant_id, name=f"runtime-rollback-{tenant_id}"))
            session.commit()

        principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)

        def principal_provider(request: Request):
            return principal

        def fail_outbox_add(self, message):
            raise RuntimeError("injected outbox failure for rollback verification")

        monkeypatch.setattr(SQLAlchemyOutboxRepository, "add", fail_outbox_add)
        app = build_runtime_app(
            database_url=DATABASE_URL,
            authorization=AllowCreateCase(),
            principal_provider=principal_provider,
        )
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/decision-cases",
                headers={"Idempotency-Key": f"runtime-rollback-{uuid4()}"},
                json={"case_type": "PROJECT_MARGIN_RISK", "title": title},
            )
            assert response.status_code == 500, response.text

        with seed_factory() as session:
            persisted = session.scalar(
                select(DecisionCaseModel).where(
                    DecisionCaseModel.tenant_id == tenant_id,
                    DecisionCaseModel.title == title,
                )
            )
            assert persisted is None, "case must roll back when the outbox write fails"
    finally:
        engine.dispose()



def test_runtime_handles_overlapping_http_commands_with_independent_transactions(monkeypatch):
    from decision_os.infrastructure.persistence.repositories.reliability import SQLAlchemyOutboxRepository

    tenant_id, actor_id = uuid4(), uuid4()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    seed_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    rendezvous = Barrier(2)
    titles = [f"Concurrent HTTP case {uuid4()}" for _ in range(2)]

    try:
        with seed_factory() as session:
            session.add(TenantModel(id=tenant_id, name=f"runtime-concurrent-{tenant_id}"))
            session.commit()

        principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)

        def principal_provider(request: Request):
            return principal

        original_add = SQLAlchemyOutboxRepository.add

        def synchronized_add(self, message):
            # Keep both command transactions in-flight together so the test exercises
            # overlapping HTTP requests rather than merely sequential requests.
            rendezvous.wait(timeout=10)
            return original_add(self, message)

        monkeypatch.setattr(SQLAlchemyOutboxRepository, "add", synchronized_add)
        app = build_runtime_app(
            database_url=DATABASE_URL,
            authorization=AllowCreateCase(),
            principal_provider=principal_provider,
        )

        with TestClient(app) as client:
            def create_case(index: int):
                return client.post(
                    "/api/v1/decision-cases",
                    headers={"Idempotency-Key": f"runtime-concurrent-{uuid4()}"},
                    json={"case_type": "PROJECT_MARGIN_RISK", "title": titles[index]},
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(create_case, index) for index in range(2)]
                responses = [future.result(timeout=20) for future in futures]

        assert [response.status_code for response in responses] == [201, 201], [
            response.text for response in responses
        ]

        with seed_factory() as session:
            persisted = session.scalars(
                select(DecisionCaseModel).where(
                    DecisionCaseModel.tenant_id == tenant_id,
                    DecisionCaseModel.title.in_(titles),
                )
            ).all()
            assert {case.title for case in persisted} == set(titles)
    finally:
        engine.dispose()



def test_runtime_triage_route_persists_with_tenant_scope_and_idempotency():
    tenant_id, actor_id, other_tenant_id = uuid4(), uuid4(), uuid4()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    seed_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    title = f"Runtime triage {uuid4()}"
    try:
        with seed_factory() as session:
            session.add_all([
                TenantModel(id=tenant_id, name=f"runtime-triage-{tenant_id}"),
                TenantModel(id=other_tenant_id, name=f"runtime-triage-other-{other_tenant_id}"),
            ])
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
                headers={"Idempotency-Key": f"runtime-triage-create-{uuid4()}"},
                json={"case_type": "PROJECT_MARGIN_RISK", "title": title},
            )
            assert created.status_code == 201, created.text
            case_id = created.json()["data"]["id"]

            triage_key = f"runtime-triage-{uuid4()}"
            first = client.post(
                f"/api/v1/decision-cases/{case_id}/triage",
                headers={"Idempotency-Key": triage_key},
            )
            assert first.status_code == 200, first.text
            assert first.json()["data"]["status"] == "TRIAGED"
            assert first.json()["data"]["version"] == 1
            assert first.headers["X-Correlation-ID"] == first.json()["correlation_id"]

            replay = client.post(
                f"/api/v1/decision-cases/{case_id}/triage",
                headers={"Idempotency-Key": triage_key},
            )
            assert replay.status_code == 200, replay.text
            assert replay.json()["data"]["status"] == "TRIAGED"

        with seed_factory() as session:
            persisted = session.scalar(
                select(DecisionCaseModel).where(
                    DecisionCaseModel.id == UUID(case_id),
                    DecisionCaseModel.tenant_id == tenant_id,
                )
            )
            assert persisted is not None
            assert persisted.status == "TRIAGED"
            assert persisted.version == 1

        other_principal = AuthenticatedPrincipal(actor_id=uuid4(), tenant_id=other_tenant_id)

        def other_principal_provider(request: Request):
            return other_principal

        other_app = build_runtime_app(
            database_url=DATABASE_URL,
            authorization=AllowCreateCase(),
            principal_provider=other_principal_provider,
        )
        with TestClient(other_app) as other_client:
            denied = other_client.post(
                f"/api/v1/decision-cases/{case_id}/triage",
                headers={"Idempotency-Key": f"runtime-cross-tenant-triage-{uuid4()}"},
            )
            assert denied.status_code == 404, denied.text
    finally:
        engine.dispose()
