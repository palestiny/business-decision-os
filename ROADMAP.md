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
- [ ] Decision memory projection

## Stage 7 — Abstraction validation
- [x] RESOURCE_CAPACITY_RISK
- [x] REVENUE_BILLING_LEAKAGE
- [x] Confirm Decision Core works without architectural change

### Current status

**Stage 7 abstraction validation is complete.**

Validated cases:
- PROJECT_MARGIN_RISK
- RESOURCE_CAPACITY_RISK
- REVENUE_BILLING_LEAKAGE

Both materially different validation cases added after the first slice reused the existing Decision Core without architectural expansion.

### Next planning decision

Prioritize product value rather than adding case types solely for abstraction validation. Candidate next areas:

1. Decision Memory projection.
2. Production-grade API/product surface.
3. Another domain capability only when a concrete requirement exposes a reusable-domain gap.

## Explicitly deferred
- AI agents
- Native ERP integrations
- Graph database
- Microservices
- Full event sourcing
- Autonomous approval/execution
