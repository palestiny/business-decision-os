# Decision Work Queue Usability and Pagination Design Gate

## Status

**OPEN — THE CURRENT QUEUE IS TENANT-SCOPED AND CORRECT FOR THE VERIFIED SLICE, BUT RETURNS AN UNBOUNDED RESULT SET.**

The current GET /api/v1/decision-work-queue returns every matching case. The persistence reader loads joined case/decision/action rows, deduplicates and sorts them in application memory, then serializes the full list. This is acceptable for the first small test dataset, not for tenants with large case volumes.

This gate covers bounded retrieval and operator-facing query ergonomics only. It does not authorize a second workflow aggregate, a new source of truth, or a frontend framework decision.

## Invariants

- Decision Core persistence remains the authoritative source of lifecycle state.
- Tenant scope comes only from the authenticated principal; no request parameter can widen tenant scope.
- The existing RBAC permission and durable authorization audit remain required on every queue read.
- Ordering must be deterministic within each response.
- Pagination must happen in the database before materializing the complete tenant queue in application memory.
- Queue reads remain read-only and must not transition cases or actions.
- API responses preserve the existing case/decision fields and correlation ID unless a versioned contract change is explicitly approved.
- Queue pages are live views, not immutable snapshots; operators should refresh after commands that change a case's attention state.

## Options

| Option | Benefits | Costs / risks | Fit |
|---|---|---|---|
| A. Bounded offset pagination | Simple limit + offset; easy for page-number UIs | Large offsets become expensive; inserts and state changes can shift page boundaries | Suitable for small, mostly static lists |
| B. Keyset/cursor pagination | Bounded query cost, avoids large offsets, works with deterministic ordering | Cursor contract and mutable priority semantics need explicit documentation; page-number jumps are not supported | **Recommended for an operational queue that can grow substantially** |
| C. Queue projection/read model | Fast filtering and richer operator metrics at scale | Introduces projection lag, rebuild/reconciliation, freshness indicators, and another operational component | Defer until measured query load justifies it |

## Recommended first contract (Option B)

1. Add optional filters for attention_state and case_type; reject unknown enum values instead of silently ignoring them.
2. Default limit=50, maximum limit=100.
3. Return data, next_cursor (nullable), and correlation_id. An opaque, versioned cursor represents the last ordering key; it must not carry tenant authority.
4. Preserve priority ordering followed by case UUID as the stable tie-breaker. Validate cursor structure and reject malformed/unsupported versions with the standard client-error contract.
5. Push filters, deterministic ordering, and the page bound into SQL. Avoid loading every tenant case and then slicing in Python.
6. Use a bounded join/subquery strategy that prevents multiple actions from duplicating a case or corrupting page boundaries.
7. Document live-page semantics: because attention priority can change between requests, a case may move between pages; refresh after an action. Do not claim snapshot consistency.
8. Add PostgreSQL integration tests for first/next page, no duplicates in an unchanged dataset, filter composition, tenant isolation, deterministic ordering, malformed cursors, and query failure/session cleanup.
9. Keep projection_state semantics explicit; it remains null while the reader queries authoritative tables directly.

## Open decision

- [ ] Approve Option B and the defaults above.
- [ ] Choose Option A if page-number navigation is a firm first-release requirement.
- [ ] Defer all pagination only if the initial product explicitly caps each tenant's active decision cases and enforces that cap.

## Acceptance criteria

- No unbounded queue API response.
- Database-side filtering/order/limit are tested, not merely response slicing.
- Cursor values cannot alter tenant scope or bypass authorization.
- Existing queue behavior remains compatible for the first page and preserves correlation IDs.
- Unit and PostgreSQL integration tests pass on supported Python versions.
- Runtime/security gates remain open until deployment controls are verified.

## Dependencies

- docs/gates/HUMAN_DECISION_WORKFLOW_DESIGN_GATE.md
- docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md
- docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md

Do not introduce a queue projection or separate workflow model as a shortcut for pagination.
