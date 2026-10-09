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
from decision_os.application.ports.authority import ApprovalDecision, Permission
from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


class AllowCreateCase:
    def require(self, *, actor_id, tenant_id, permission, resource_id, correlation_id=None):
        assert permission in {Permission.CREATE_CASE, Permission.TRIAGE_CASE, Permission.START_ANALYSIS, Permission.CREATE_EVIDENCE, Permission.ADD_ANALYSIS, Permission.SUBMIT_OPTIONS, Permission.AWAIT_DECISION, Permission.MAKE_DECISION, Permission.APPROVE_DECISION, Permission.REJECT_DECISION, Permission.CREATE_ACTION, Permission.START_ACTION, Permission.VIEW_DECISION_WORK_QUEUE}


class RequireApprovalPolicy:
    def evaluate(self, *, actor_id, tenant_id, case_id):
        return ApprovalDecision(required=True)



def test_runtime_reject_decision_is_persisted_and_idempotent():
    from datetime import datetime, timezone
    from decision_os.infrastructure.persistence.models.decision import DecisionModel, DecisionOptionModel, DecisionSelectedOptionModel
    from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel

    tenant_id, creator_id, decision_maker_id, rejector_id = uuid4(), uuid4(), uuid4(), uuid4()
    case_id, decision_id, option_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    try:
        with factory() as session:
            session.add(TenantModel(id=tenant_id, name=f"runtime-reject-{tenant_id}"))
            session.flush()
            session.add(DecisionCaseModel(
                id=case_id, tenant_id=tenant_id, case_type="PROJECT_MARGIN_RISK",
                title="Reject decision runtime test", created_by=creator_id,
                status="AWAITING_APPROVAL", version=1, created_at=now, updated_at=now,
            ))
            session.flush()
            session.add(DecisionOptionModel(id=option_id, case_id=case_id, title="Candidate option"))
            session.add(DecisionModel(
                id=decision_id, case_id=case_id, status="AWAITING_APPROVAL",
                rationale="Candidate rationale", decided_by=decision_maker_id,
                decided_at=now, created_at=now, approval_required=True,
                authority_snapshot='{"approval_required": true, "policy_ids": []}',
            ))
            session.flush()
            session.add(DecisionSelectedOptionModel(decision_id=decision_id, option_id=option_id))
            session.commit()

        principal = AuthenticatedPrincipal(actor_id=rejector_id, tenant_id=tenant_id)
        def principal_provider(request: Request):
            return principal
        app = build_runtime_app(database_url=DATABASE_URL, authorization=AllowCreateCase(), principal_provider=principal_provider)
        key = f"runtime-reject-decision-{uuid4()}"
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/decision-cases/{case_id}/decision/{decision_id}/reject",
                headers={"Idempotency-Key": key},
            )
            assert response.status_code == 200, response.text
            assert response.json()["data"]["status"] == "REJECTED"
            assert response.headers["X-Correlation-ID"] == response.json()["correlation_id"]
            replay = client.post(
                f"/api/v1/decision-cases/{case_id}/decision/{decision_id}/reject",
                headers={"Idempotency-Key": key},
            )
            assert replay.status_code == 200, replay.text
            assert replay.json()["data"]["status"] == "REJECTED"

        with factory() as session:
            case = session.get(DecisionCaseModel, case_id)
            decision = session.get(DecisionModel, decision_id)
            assert case is not None and case.status == "REJECTED" and case.version == 2
            assert decision is not None and decision.status == "REJECTED"
    finally:
        engine.dispose()


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
            assert denied.status_code == 409, denied.text
            assert denied.json()["error"]["code"] == "DOMAIN_CONFLICT"
            assert case_id not in denied.text
    finally:
        engine.dispose()



def test_runtime_start_analysis_and_evidence_routes_are_composed_and_persisted():
    tenant_id, actor_id = uuid4(), uuid4()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    seed_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    title = f"Runtime analysis and evidence {uuid4()}"
    try:
        with seed_factory() as session:
            session.add(TenantModel(id=tenant_id, name=f"runtime-analysis-evidence-{tenant_id}"))
            session.commit()

        principal = AuthenticatedPrincipal(actor_id=actor_id, tenant_id=tenant_id)

        def principal_provider(request: Request):
            return principal

        app = build_runtime_app(
            database_url=DATABASE_URL,
            authorization=AllowCreateCase(),
            principal_provider=principal_provider,
            policy_evaluator=RequireApprovalPolicy(),
        )
        evidence_id = uuid4()
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/decision-cases",
                headers={"Idempotency-Key": f"runtime-analysis-create-{uuid4()}"},
                json={"case_type": "PROJECT_MARGIN_RISK", "title": title},
            )
            assert created.status_code == 201, created.text
            case_id = created.json()["data"]["id"]

            triaged = client.post(
                f"/api/v1/decision-cases/{case_id}/triage",
                headers={"Idempotency-Key": f"runtime-analysis-triage-{uuid4()}"},
            )
            assert triaged.status_code == 200, triaged.text
            assert triaged.json()["data"]["status"] == "TRIAGED"

            analysis_key = f"runtime-analysis-{uuid4()}"
            first = client.post(
                f"/api/v1/decision-cases/{case_id}/analysis/start",
                headers={"Idempotency-Key": analysis_key},
            )
            assert first.status_code == 200, first.text
            assert first.json()["data"]["status"] == "ANALYZING"
            assert first.json()["data"]["version"] == 2
            assert first.headers["X-Correlation-ID"] == first.json()["correlation_id"]

            replay = client.post(
                f"/api/v1/decision-cases/{case_id}/analysis/start",
                headers={"Idempotency-Key": analysis_key},
            )
            assert replay.status_code == 200, replay.text
            assert replay.json()["data"]["status"] == "ANALYZING"

            evidence_response = client.post(
                f"/api/v1/decision-cases/{case_id}/evidence",
                headers={"Idempotency-Key": f"runtime-evidence-{uuid4()}"},
                json={
                    "evidence_id": str(evidence_id),
                    "source": "project-system",
                    "metric": "forecast_margin",
                    "value": "12.5",
                    "unit": "percent",
                    "period": "2026-10",
                    "captured_at": "2026-10-09T08:00:00+00:00",
                    "confidence": 0.95,
                    "snapshot": "Approved monthly forecast snapshot",
                },
            )
            assert evidence_response.status_code == 201, evidence_response.text
            assert evidence_response.json()["data"]["id"] == str(evidence_id)
            assert evidence_response.headers["X-Correlation-ID"] == evidence_response.json()["correlation_id"]

            finding_id = uuid4()
            finding_key = f"runtime-analysis-finding-{uuid4()}"
            finding_response = client.post(
                f"/api/v1/decision-cases/{case_id}/analysis/findings",
                headers={"Idempotency-Key": finding_key},
                json={
                    "finding_id": str(finding_id),
                    "kind": "FACT",
                    "statement": "Forecast margin is below the approved threshold.",
                    "confidence": 0.97,
                    "evidence_ids": [str(evidence_id)],
                },
            )
            assert finding_response.status_code == 201, finding_response.text
            assert finding_response.json()["data"]["id"] == str(finding_id)
            assert finding_response.json()["data"]["evidence_ids"] == [str(evidence_id)]
            assert finding_response.headers["X-Correlation-ID"] == finding_response.json()["correlation_id"]

            finding_replay = client.post(
                f"/api/v1/decision-cases/{case_id}/analysis/findings",
                headers={"Idempotency-Key": finding_key},
                json={
                    "finding_id": str(finding_id),
                    "kind": "FACT",
                    "statement": "Forecast margin is below the approved threshold.",
                    "confidence": 0.97,
                    "evidence_ids": [str(evidence_id)],
                },
            )
            assert finding_replay.status_code == 201, finding_replay.text
            assert finding_replay.json()["data"]["id"] == str(finding_id)

            option_ids = [uuid4(), uuid4()]
            option_payload = [
                {"id": str(option_ids[0]), "title": "Reduce discretionary spend"},
                {"id": str(option_ids[1]), "title": "Renegotiate supplier terms"},
            ]
            options_key = f"runtime-submit-options-{uuid4()}"
            options_response = client.post(
                f"/api/v1/decision-cases/{case_id}/options",
                headers={"Idempotency-Key": options_key},
                json=option_payload,
            )
            assert options_response.status_code == 200, options_response.text
            assert options_response.json()["data"]["status"] == "OPTIONS_READY"
            assert options_response.json()["data"]["version"] == 3
            assert {item["id"] for item in options_response.json()["data"]["options"]} == {
                str(value) for value in option_ids
            }

            options_replay = client.post(
                f"/api/v1/decision-cases/{case_id}/options",
                headers={"Idempotency-Key": options_key},
                json=option_payload,
            )
            assert options_replay.status_code == 200, options_replay.text
            assert options_replay.json()["data"]["status"] == "OPTIONS_READY"

            await_key = f"runtime-await-decision-{uuid4()}"
            await_response = client.post(
                f"/api/v1/decision-cases/{case_id}/decision/await",
                headers={"Idempotency-Key": await_key},
            )
            assert await_response.status_code == 200, await_response.text
            assert await_response.json()["data"]["status"] == "AWAITING_DECISION"
            assert await_response.json()["data"]["version"] == 4
            assert await_response.headers["X-Correlation-ID"] == await_response.json()["correlation_id"]

            await_replay = client.post(
                f"/api/v1/decision-cases/{case_id}/decision/await",
                headers={"Idempotency-Key": await_key},
            )
            assert await_replay.status_code == 200, await_replay.text
            assert await_replay.json()["data"]["status"] == "AWAITING_DECISION"

            decision_id = uuid4()
            decision_key = f"runtime-make-decision-{uuid4()}"
            decision_payload = {
                "decision_id": str(decision_id),
                "option_ids": [str(option_ids[0])],
                "rationale": "Protect the forecast margin with the selected option.",
            }
            decision_response = client.post(
                f"/api/v1/decision-cases/{case_id}/decision",
                headers={"Idempotency-Key": decision_key}, json=decision_payload,
            )
            assert decision_response.status_code == 200, decision_response.text
            assert decision_response.json()["data"]["id"] == str(decision_id)
            assert decision_response.json()["data"]["status"] == "AWAITING_APPROVAL"
            assert decision_response.json()["data"]["approval_required"] is True
            assert decision_response.headers["X-Correlation-ID"] == decision_response.json()["correlation_id"]
            decision_replay = client.post(
                f"/api/v1/decision-cases/{case_id}/decision",
                headers={"Idempotency-Key": decision_key}, json=decision_payload,
            )
            assert decision_replay.status_code == 200, decision_replay.text
            assert decision_replay.json()["data"]["id"] == str(decision_id)
            assert decision_replay.json()["data"]["status"] == "AWAITING_APPROVAL"

        approver_actor_id = uuid4()
        approver_principal = AuthenticatedPrincipal(actor_id=approver_actor_id, tenant_id=tenant_id)
        def approver_provider(request: Request):
            return approver_principal
        approver_app = build_runtime_app(
            database_url=DATABASE_URL,
            authorization=AllowCreateCase(),
            principal_provider=approver_provider,
            policy_evaluator=RequireApprovalPolicy(),
        )
        approval_key = f"runtime-approve-decision-{uuid4()}"
        with TestClient(approver_app) as approver_client:
            approval_response = approver_client.post(
                f"/api/v1/decision-cases/{case_id}/decision/{decision_id}/approve",
                headers={"Idempotency-Key": approval_key},
            )
            assert approval_response.status_code == 200, approval_response.text
            assert approval_response.json()["data"]["status"] == "APPROVED"
            assert approval_response.json()["data"]["approved_by"] == str(approver_actor_id)
            assert approval_response.headers["X-Correlation-ID"] == approval_response.json()["correlation_id"]
            approval_replay = approver_client.post(
                f"/api/v1/decision-cases/{case_id}/decision/{decision_id}/approve",
                headers={"Idempotency-Key": approval_key},
            )
            assert approval_replay.status_code == 200, approval_replay.text
            assert approval_replay.json()["data"]["status"] == "APPROVED"

            action_id = uuid4()
            action_key = f"runtime-create-action-{uuid4()}"
            action_payload = {
                "decision_id": str(decision_id),
                "action_id": str(action_id),
                "action_type": "COST_REDUCTION",
                "parameters": "Reduce discretionary spend by 5 percent",
            }
            action_response = approver_client.post(
                f"/api/v1/decision-cases/{case_id}/actions",
                headers={"Idempotency-Key": action_key}, json=action_payload,
            )
            assert action_response.status_code == 201, action_response.text
            assert action_response.json()["data"]["id"] == str(action_id)
            assert action_response.json()["data"]["status"] == "READY"
            assert action_response.json()["data"]["version"] == 1
            assert action_response.headers["X-Correlation-ID"] == action_response.json()["correlation_id"]
            action_replay = approver_client.post(
                f"/api/v1/decision-cases/{case_id}/actions",
                headers={"Idempotency-Key": action_key}, json=action_payload,
            )
            assert action_replay.status_code == 201, action_replay.text
            assert action_replay.json()["data"]["id"] == str(action_id)
            assert action_replay.json()["data"]["status"] == "READY"

            execution_key = f"runtime-start-action-{uuid4()}"
            execution_response = approver_client.post(
                f"/api/v1/actions/{action_id}/start",
                headers={"Idempotency-Key": execution_key},
            )
            assert execution_response.status_code == 200, execution_response.text
            assert execution_response.json()["data"]["action_id"] == str(action_id)
            assert execution_response.json()["data"]["attempt"] == 1
            assert execution_response.json()["data"]["status"] == "RUNNING"
            assert execution_response.headers["X-Correlation-ID"] == execution_response.json()["correlation_id"]
            execution_replay = approver_client.post(
                f"/api/v1/actions/{action_id}/start",
                headers={"Idempotency-Key": execution_key},
            )
            assert execution_replay.status_code == 200, execution_replay.text
            assert execution_replay.json()["data"]["id"] == execution_response.json()["data"]["id"]
            assert execution_replay.json()["data"]["status"] == "RUNNING"

        with seed_factory() as session:
            case_row = session.scalar(
                select(DecisionCaseModel).where(
                    DecisionCaseModel.id == UUID(case_id),
                    DecisionCaseModel.tenant_id == tenant_id,
                )
            )
            assert case_row is not None
            assert case_row.status == "EXECUTING"
            assert case_row.version == 8

            from decision_os.infrastructure.persistence.models.decision import DecisionModel
            decision_row = session.scalar(select(DecisionModel).where(DecisionModel.id == decision_id))
            assert decision_row is not None
            assert decision_row.status == "APPROVED"
            assert decision_row.approval_required is True
            assert decision_row.approved_by == approver_actor_id
            assert decision_row.approved_at is not None

            from decision_os.infrastructure.persistence.models.action import ActionModel
            action_row = session.get(ActionModel, action_id)
            assert action_row is not None
            assert action_row.case_id == UUID(case_id)
            assert action_row.decision_id == decision_id
            assert action_row.status == "EXECUTING"
            assert action_row.version == 2

            from decision_os.infrastructure.persistence.models.action import ActionExecutionModel
            execution_row = session.get(ActionExecutionModel, UUID(execution_response.json()["data"]["id"]))
            assert execution_row is not None
            assert execution_row.action_id == action_id
            assert execution_row.attempt == 1
            assert execution_row.status == "RUNNING"

            from decision_os.infrastructure.persistence.models.decision import DecisionOptionModel
            persisted_options = session.scalars(
                select(DecisionOptionModel).where(DecisionOptionModel.case_id == UUID(case_id))
            ).all()
            assert {row.id for row in persisted_options} == set(option_ids)

            from decision_os.infrastructure.persistence.models.evidence import EvidenceModel
            evidence_row = session.scalar(
                select(EvidenceModel).where(
                    EvidenceModel.id == evidence_id,
                    EvidenceModel.tenant_id == tenant_id,
                    EvidenceModel.case_id == UUID(case_id),
                )
            )
            assert evidence_row is not None
            assert evidence_row.metric == "forecast_margin"
            assert evidence_row.value == "12.5"

            from decision_os.infrastructure.persistence.models.evidence import AnalysisFindingModel
            finding_row = session.scalar(
                select(AnalysisFindingModel).where(
                    AnalysisFindingModel.id == finding_id,
                    AnalysisFindingModel.tenant_id == tenant_id,
                    AnalysisFindingModel.case_id == UUID(case_id),
                )
            )
            assert finding_row is not None
            assert finding_row.kind == "FACT"
            assert finding_row.statement == "Forecast margin is below the approved threshold."
    finally:
        engine.dispose()
