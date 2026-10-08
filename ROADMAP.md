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
- [x] Runtime composition design gate documented
- [ ] Deployment composition root / request-scoped database reader wiring
- [ ] Product-facing queue usability and operator workflow

**Status: Stage 10 read-only queue slice PASS; runtime composition design defined, implementation and verification pending.** Evidence for queue: commit `870995158a1fae799241408cf39b95bae52e2e49`, CI Run #806: https://github.com/palestiny/business-decision-os/actions/runs/37850119985. Runtime design: `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`.

## Explicitly deferred
- AI agents and AI authority
- Native ERP integrations
- Graph database
- Microservices
- Full event sourcing
- Autonomous approval/execution
- Vector/embedding memory
- Durable organizational Learning until justified by demonstrated requirements
