# HUMAN DECISION WORKFLOW DESIGN GATE

## Status
**DESIGN-LOCKED — implementation pending RED verification.**

## Objective
Extend Decision OS from lifecycle recording and history consumption into a focused human decision workflow without introducing a second source of truth.

The first Stage 10 slice is a tenant-scoped **Decision Work Queue** that identifies cases requiring human attention and exposes enough current context to route the user into the existing Decision Core commands.

## Product boundary
Decision OS remains a decision-and-execution layer, not an ERP.

The work queue is a consumption/query concern. Decision Core remains authoritative for case state, decisions, approvals, actions, outcomes, and verification.

## Scope
### In scope
- Tenant-scoped work queue query.
- Deterministic identification of cases requiring human attention.
- Explicit workflow attention states derived from authoritative current state.
- Current case identity/type/title/status.
- Decision/approval context required for human routing.
- Projection/version state where relevant.
- Deterministic ordering.
- Existing authentication and tenant isolation.
- Read-only queue; commands continue through existing reliability boundaries.
- Unit tests and PostgreSQL integration tests.

### Out of scope
- New Decision aggregate.
- New approval authority model.
- Autonomous decisions.
- AI recommendations or AI authority.
- ERP/CRM/PSA integrations.
- Notifications or external messaging.
- Generic workflow/rules engine.
- Cross-tenant queues.
- Durable Learning.
- Event sourcing, graph storage, vector memory, microservices.
- Replacing Decision Memory or Decision Core.

## Workflow attention model
The queue must expose a small explicit attention classification rather than requiring clients to reverse-engineer lifecycle state.

Initial attention states:
- REVIEW_CASE — case requires human review before progressing.
- MAKE_DECISION — options are available and a decision is required.
- APPROVE_DECISION — a decision exists and approval is required.
- EXECUTE_ACTION — an approved decision has an action ready for execution.
- REVIEW_OUTCOME — execution/outcome exists and human review or verification is pending.
- NO_ACTION — not eligible for the work queue.

The exact mapping must be derived from existing authoritative domain state and existing command preconditions. It must not invent a parallel lifecycle.

## Queue contract
Each item must contain at minimum:
- tenant-scoped case ID;
- case type;
- title;
- current case status;
- attention state;
- relevant decision ID when present;
- decision status when present;
- approval-required/status when present;
- authoritative version;
- projection state when available.

Ordering must be deterministic. The initial contract should prefer explicit lifecycle priority followed by stable case identity rather than wall-clock ordering.

## Safety and authority
1. Queue reads never mutate authoritative state.
2. Queue classification cannot approve, decide, execute, or close a case.
3. Existing Decision Core commands remain the only mutation path.
4. Tenant ID comes from the authenticated principal.
5. A case belonging to another tenant must be indistinguishable from not-found/not-visible to the queue.
6. Stale Decision Memory must not silently be presented as authoritative current business state.
7. If authoritative state and projection state disagree, the response must expose the projection state rather than hiding it.
8. No AI output is treated as a decision or approval.

## Verification
The gate can move beyond DESIGN-LOCKED only after:
1. RED tests define the queue contract.
2. GREEN implementation reuses existing domain/application boundaries.
3. Unit tests prove attention classification and deterministic ordering.
4. PostgreSQL integration proves tenant isolation and real persistence.
5. Existing reliability and API test suites remain green.
6. Supported Python CI and migration checks pass.
7. Documentation records the verified implementation and evidence.

## Design decision
**Decision:** Build the smallest read-only, tenant-scoped human decision work queue on top of existing Decision Core/Decision Memory capabilities.

**Rejected:** introducing a generic workflow engine, task aggregate, notification subsystem, or new transactional workflow model at this stage.

**Rationale:** the repository already contains the lifecycle commands required to act. The missing product capability is primarily consumption/routing of those commands, not another domain model.

## Next implementation step
TDD RED only:
- define a work-queue reader contract;
- define representative attention states from existing lifecycle states;
- prove tenant isolation and deterministic ordering;
- do not add production architecture until RED exposes a concrete missing boundary.