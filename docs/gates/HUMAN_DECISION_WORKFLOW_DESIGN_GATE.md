# HUMAN DECISION WORKFLOW DESIGN GATE

## Status
**IMPLEMENTATION PASS — verified by CI Run #806.** The read-only tenant-scoped queue slice is implemented. This gate does not claim a deployable production composition root: the repository exposes an application factory and dependency-injection contracts, while deployment-specific assembly remains outside the current repository.

## Objective
Extend Decision OS from lifecycle recording and history consumption into a focused human decision workflow without introducing a second source of truth.

The first Stage 10 slice is a tenant-scoped **Decision Work Queue** that identifies cases requiring human attention and exposes enough current context to route the user into the existing Decision Core commands.

## Product boundary
Decision OS remains a decision-and-execution layer, not an ERP. The queue is a read-only query over authoritative Decision Core persistence; it does not introduce a second lifecycle or mutation path.

## Implemented contract
- Reader port: `DecisionWorkQueueReader.list(tenant_id=...)`.
- PostgreSQL reader: `SQLAlchemyDecisionWorkQueueReader`.
- API: `GET /api/v1/decision-work-queue`, registered by `create_app` when a reader is injected.
- Response includes case ID/type/title/status, attention state, decision context, authoritative case version, projection state (null for this direct-authoritative query), and correlation ID.
- Tenant ID comes only from the authenticated principal.
- Deterministic ordering: attention priority, then stable case UUID.
- Approved cases are classified as `EXECUTE_ACTION` only when a tenant-matching action is `READY`; otherwise they are excluded.
- Queue reads do not mutate state; existing Decision Core commands remain the mutation path.

## Attention mapping
- `DETECTED`, `TRIAGED`, `ANALYZING`, `OPTIONS_READY` → `REVIEW_CASE`
- `AWAITING_DECISION` → `MAKE_DECISION`
- `AWAITING_APPROVAL` → `APPROVE_DECISION`
- `APPROVED` with a `READY` action → `EXECUTE_ACTION`
- `OUTCOME_PENDING`, `VERIFYING` → `REVIEW_OUTCOME`
- Other states → `NO_ACTION` and are not returned.

## Verification evidence
- Unit tests cover attention mapping and deterministic priority ordering.
- PostgreSQL integration tests cover tenant isolation, exclusion of approved cases without a ready action, and inclusion when a ready action exists.
- CI Run #806 succeeded on commit `870995158a1fae799241408cf39b95bae52e2e49`: https://github.com/palestiny/business-decision-os/actions/runs/37850119985
- CI success verifies the current test workflow; it does not establish deployment-level composition or live production behavior.

## Explicit limitations / follow-up
1. No deployment composition root is present in the repository tree. A deployable entry point must inject a request-lifecycle-safe session/reader when runtime packaging is added; do not create a global long-lived SQLAlchemy Session.
2. `projection_state` is null because this slice queries authoritative Decision Core tables directly instead of Decision Memory. This is intentional and must not be interpreted as projection freshness.
3. Notifications, a generic workflow engine, a task aggregate, AI authority, external ERP/CRM integrations, and autonomous actions remain out of scope.

## Decision
**Keep the smallest read-only, tenant-scoped work queue.** Do not add a second workflow model or transactional source of truth. Continue with runtime composition and product-facing usability only when the application entry-point/deployment boundary is introduced and designed.
