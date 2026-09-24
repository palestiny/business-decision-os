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
- [ ] Project skeleton
- [ ] Domain primitives
- [ ] Application command/query contracts
- [ ] Tenant context
- [ ] Error model
- [ ] Clock and ID abstractions
- [ ] Architecture tests

## Stage 2 — Decision Core
- [ ] DecisionCase
- [ ] Case lifecycle
- [ ] Evidence
- [ ] Analysis findings
- [ ] Options
- [ ] Decision
- [ ] Approval

## Stage 3 — Reliability
- [ ] Unit of Work
- [ ] Idempotency
- [ ] Optimistic concurrency
- [ ] Domain events
- [ ] Transactional outbox
- [ ] Append-only audit

## Stage 4 — Execution and Outcomes
- [ ] Action
- [ ] ActionExecution
- [ ] Retry / UNKNOWN / reconciliation
- [ ] Expected outcomes
- [ ] Actual outcomes
- [ ] Verification
- [ ] Closure

## Stage 5 — API
- [ ] REST contracts
- [ ] Authentication
- [ ] Authorization
- [ ] Tenant isolation
- [ ] Idempotency contract
- [ ] Error contract

## Stage 6 — First vertical slice
- [ ] PROJECT_MARGIN_RISK end-to-end
- [ ] Synthetic controlled dataset
- [ ] Full audit trail
- [ ] Verification
- [ ] Decision memory projection

## Stage 7 — Abstraction validation
- [ ] RESOURCE_CAPACITY_RISK
- [ ] REVENUE_BILLING_LEAKAGE
- [ ] Confirm Decision Core works without architectural change

## Explicitly deferred
- AI agents
- Native ERP integrations
- Graph database
- Microservices
- Full event sourcing
- Autonomous approval/execution
