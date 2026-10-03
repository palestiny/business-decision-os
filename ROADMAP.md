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

### Current status

**Stage 7 complete. Stage 8 Decision Memory implementation is complete and gated PASS.**

## Stage 8 — Decision Memory
- [x] Source-of-truth model
- [x] Projection consistency model
- [x] Projection event/update contract
- [x] Tenant isolation
- [x] Idempotent projection updates
- [x] Rebuild/reconciliation semantics
- [x] Decision history query contract
- [x] PostgreSQL projection implementation
- [x] API query surface
- [x] Projection failure/lag verification
- [x] CI verification

### Current work

**Decision Memory Design Gate: PASS.**

Evidence: gate closed in commit 3ecc8e8409fc0b368428297b57745cb6264e0786; CI Run #762 (37155367148) passed on Python 3.12 and 3.13 with PostgreSQL migration lifecycle, alembic check, and full pytest.

## Explicitly deferred
- AI agents
- Native ERP integrations
- Graph database
- Microservices
- Full event sourcing
- Autonomous approval/execution
- Vector/embedding memory
