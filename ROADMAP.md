# Roadmap

## Stage 0 — Product and architecture definition
- [x] ERP / market gap research
- [x] Decision OS product thesis
- [x] Decision lifecycle
- [x] Domain model
- [x] Human authority and approval model
- [x] Execution reliability model
- [x] Outcome and verification model
- [x] Application architecture
- [x] PostgreSQL strategy
- [x] First vertical slice definition

## Stage 1 — Foundation
- [x] Project skeleton
- [x] Domain primitives
- [x] Application command/query contracts
- [x] Tenant context
- [x] Error model
- [x] Clock and ID policy decision (abstractions deferred)
- [x] Architecture tests

## Stage 2 — Decision Core
- [x] DecisionCase
- [x] Case lifecycle
- [x] Evidence
- [x] Analysis findings
- [x] Options
- [x] Decision
- [x] Approval

## Stage 3 — Reliability
- [x] Unit of Work
- [x] Idempotency
- [x] Optimistic concurrency
- [ ] Domain events
- [x] Transactional outbox
- [x] Append-only audit

## Stage 4 — Execution and Outcomes
- [x] Action
- [x] ActionExecution
- [x] Retry / UNKNOWN / reconciliation
- [x] Expected outcomes
- [x] Actual outcomes
- [x] Verification
- [x] Closure

## Stage 5 — API
- [x] REST contracts
- [x] Authentication boundary
- [x] Authorization boundary
- [x] Tenant isolation
- [x] Idempotency contract
- [x] Error contract

## Stage 6 — First vertical slice
- [x] PROJECT_MARGIN_RISK end-to-end
- [x] Synthetic controlled dataset foundation
- [x] Full audit trail
- [x] Verification
- [x] Decision memory projection

## Stage 7 — Abstraction validation
- [x] RESOURCE_CAPACITY_RISK
- [x] REVENUE_BILLING_LEAKAGE
- [x] Confirm Decision Core works without architectural change

## Stage 8 — Decision Memory
- [x] Source-of-truth model
- [x] Projection consistency model
- [x] Tenant isolation
- [x] Idempotent projection updates
- [x] Rebuild/reconciliation semantics
- [x] Decision history query contract
- [x] PostgreSQL projection implementation
- [x] API query surface
- [x] Projection failure/lag verification
- [x] CI verification

**Status: PASS.** Evidence: gate closed in commit `3ecc8e8409fc0b368428297b57745cb6264e0786`; CI Run #762 passed on Python 3.12/3.13 with PostgreSQL migration lifecycle, Alembic check, and full pytest.

## Stage 9 — Decision Learning & History
- [x] Decision History query contract
- [x] Coherent tenant-scoped history narrative
- [x] Verified vs unverified outcome distinction
- [x] PostgreSQL integration and tenant isolation
- [x] Supported-Python CI verification
- [x] Learning boundary kept read-only
- [ ] Durable organizational Learning — deferred pending demonstrated business requirement

**Status: History slice PASS; durable Learning intentionally deferred.** Evidence: CI Run #776 (`37617676754`).

## Stage 10 — Human Decision Workflow
- [x] Read-only tenant-scoped work queue port
- [x] PostgreSQL-backed reader using authoritative case/decision/action state
- [x] Explicit attention classification
- [x] Deterministic priority and stable tie-break ordering
- [x] API endpoint `GET /api/v1/decision-work-queue`
- [x] Unit tests for mapping and ordering
- [x] PostgreSQL integration coverage for tenant isolation and ready-action eligibility
- [x] CI verification — Run #806
- [x] Runtime composition root for create-case + work queue
- [x] Request/use-case-scoped Session for create-case persistence adapters
- [x] Query-scoped Session lifecycle for work queue
- [x] PostgreSQL HTTP create-case → same-tenant queue visibility
- [x] PostgreSQL HTTP cross-tenant queue isolation
- [x] Runtime composition slice CI on Python 3.12 and 3.13 — Runs #844/#845
- [x] Unit-level concurrent command isolation (distinct Sessions and cleanup; CI #854/#855)
- [x] PostgreSQL-backed overlapping HTTP create requests (both 201 and persisted; CI #870/#871, Python 3.12/3.13)
- [x] PostgreSQL rollback verification when Outbox write fails (CI #862/#863)
- [x] OIDC/JWT adapter plus database-backed external identity resolver and runtime auto-wiring (CI #938/#939 passed, Python 3.12/3.13)
- [ ] Deployment-specific authentication configuration and trusted identity-mapping provisioning policy
- [x] Implement tenant-scoped RBAC, PostgreSQL tests, permission-gated read APIs, and CI verification (#967/#968 on Python 3.12/3.13) — `docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md`
- [x] Implement offline CLI provision/show/revoke with dry-run confirmation and durable admin audit; CI #983 passed on Python 3.12/3.13 (193 tests each) — `docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md`, `docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md`, `docs/gates/AUTHORIZATION_DECISION_AUDIT_DESIGN_GATE.md`
- [x] Enforce four-eyes approval attribution and denial for creator/decision-maker/legacy cases; CI #995/#996 passed on Python 3.12/3.13 (200 tests each) — `docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md`
- [x] Implement durable allow/deny authorization decision audit with fail-closed persistence; CI #1011/#1012 passed. Command correlation propagation verified in CI #1023/#1024 (204 tests per Python version) — `docs/gates/AUTHORIZATION_DECISION_AUDIT_DESIGN_GATE.md`.
- [x] Approve audit retention/access defaults: 365 days searchable by default, restricted security/operations access, no public query API, and cleanup disabled pending legal-hold/archive design. Deployment backup/restore and privileged-access evidence remain open — `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`.
- [x] Compose triage-case with request-scoped persistence, RBAC permission checks, idempotency, audit, and outbox; CI verification pending.
- [ ] Compose additional command routes after lifecycle/authorization review
- [ ] Product-facing queue usability and operator workflow

**Status: Read-only queue PASS; first runtime composition slice implemented and CI-verified; runtime gate remains open.** Evidence: CI #844 https://github.com/palestiny/business-decision-os/actions/runs/37853330867 and CI #845 https://github.com/palestiny/business-decision-os/actions/runs/37853337025 for initial composition; CI #870 https://github.com/palestiny/business-decision-os/actions/runs/37856028446 and CI #871 https://github.com/palestiny/business-decision-os/actions/runs/37856033069 verify overlapping PostgreSQL-backed HTTP creates on Python 3.12/3.13. Rollback verification passed in CI #862/#863. OIDC runtime auto-wiring, database identity mapping, HTTP rejection tests, and Alembic migration checks passed CI #938/#939 on Python 3.12/3.13. Remaining work is tracked in `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`, `docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md`, `docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md`, `docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md`, `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`, and `docs/checkpoints/CHECKPOINT-038.md`. Durable allow/deny authorization-decision audit and fail-closed audit-write behavior passed CI #1011/#1012 on Python 3.12/3.13. Command correlation propagation passed CI #1023/#1024 (204 tests per Python version); audit retention/access and deployment configuration remain open.

## Explicitly deferred
- AI agents and AI authority
- Native ERP integrations
- Graph database
- Microservices
- Full event sourcing
- Autonomous approval/execution
- Vector/embedding memory
- Durable organizational Learning until justified by demonstrated requirements
