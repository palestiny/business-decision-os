# Business Decision OS

Business Decision Operating System (Decision OS).

## Purpose

Decision OS is not an ERP replacement. It is a decision-and-execution layer that connects business signals to evidence, analysis, decisions, controlled actions, outcomes, verification, and organizational learning.

## Core lifecycle

Signal → Case → Evidence → Analysis → Options → Decision → Approval → Action → Outcome → Verification → Learning

## Initial vertical slice

Project / Delivery Performance Decisions, starting with `PROJECT_MARGIN_RISK`.

## Architecture and implementation status

- Application Architecture Gate: PASS.
- Stages 0–9: foundation, Decision Core, reliability, vertical slices, Decision Memory, and read-only Decision History implemented and gated as recorded in `ROADMAP.md`.
- Stage 10: tenant-scoped read-only Decision Work Queue implemented; CI Run #806 passed.
- API query: `GET /api/v1/decision-work-queue`, enabled when `create_app` receives a `DecisionWorkQueueReader`.
- Runtime composition: the first slice composes create-case and the work queue with scoped SQLAlchemy Sessions. PostgreSQL HTTP tests verify same-tenant visibility and cross-tenant isolation; CI Runs #844/#845 passed on Python 3.12 and 3.13.
- Runtime verification now includes overlapping PostgreSQL-backed HTTP create requests (both 201 and persisted; CI Runs #870/#871 on Python 3.12/3.13) and rollback after an injected Outbox failure (CI #862/#863). Tenant-scoped RBAC is now implemented as the runtime default, but its CI verification is pending. The runtime gate remains open because deployment-specific OIDC settings, trusted membership/role provisioning, durable authorization audit, separation-of-duties rules, and additional command routes are not yet established; this is not a deployment-readiness claim.
- See `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`, `docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md`, `docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md`, and `docs/checkpoints/CHECKPOINT-038.md` for evidence and remaining work. This is not a deployment-readiness claim.

See `docs/gates/HUMAN_DECISION_WORKFLOW_DESIGN_GATE.md` for the queue slice scope and `ROADMAP.md` for current stage status.
