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
- Runtime verification includes overlapping PostgreSQL-backed HTTP create requests (CI #870/#871), rollback after an injected Outbox failure (CI #862/#863), tenant-scoped RBAC and permission-gated reads (CI #967/#968), and offline provisioning with transactional admin audit (CI #983). Four-eyes approval now persists case creator and approver attribution, rejects self-approval by the creator or decision maker, and fails closed for legacy cases without creator attribution. PostgreSQL migration lifecycle, Alembic check, and 200 tests per supported Python version passed CI #995/#996. The runtime gate remains open for trusted-environment operations, operational implementation/evidence for the approved audit retention/access defaults, deployment-specific OIDC settings, and additional command routes. The approved policy uses a 365-day searchable default, restricts audit access to approved security/operations operators, exposes no public audit-query API, and keeps automatic cleanup disabled pending legal-hold/archive design. Command correlation propagation is verified in CI #1023/#1024 (204 tests per supported Python version); this is not a deployment-readiness claim.
- See `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`, `docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md`, `docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md`, `docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md`, `docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md`, `docs/gates/AUTHORIZATION_DECISION_AUDIT_DESIGN_GATE.md`, `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`, and `docs/checkpoints/CHECKPOINT-038.md` for evidence and remaining work. This is not a deployment-readiness claim.

See `docs/gates/HUMAN_DECISION_WORKFLOW_DESIGN_GATE.md` for the queue slice scope and `ROADMAP.md` for current stage status.
