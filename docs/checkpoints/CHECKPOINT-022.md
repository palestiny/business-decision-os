# CHECKPOINT-022

## Scope

Reject Decision HTTP command boundary and durable reliability proof.

## Completed

- Added `RejectDecisionReliabilityBoundary`.
- Preserved transaction ownership in `ReliabilityExecutor`; `RejectDecisionHandler` remains transaction-neutral.
- Added explicit HTTP command:
  - `POST /api/v1/decision-cases/{case_id}/decision/{decision_id}/reject`
- API derives tenant and actor identity from the authenticated principal.
- `Idempotency-Key` remains required.
- `REJECT_DECISION` is the explicit authorization permission.
- Rejection remains an explicit domain transition; no generic status mutation endpoint was introduced.
- Added deterministic request hashing and replay serialization.
- Added `decision.rejected` transactional outbox event.
- Added HTTP contract tests for identity mapping, stable response, and required idempotency.
- Added PostgreSQL integration proof for:
  - rejection persistence
  - case transition to `REJECTED`
  - optimistic version increment
  - idempotent replay
  - exactly one audit event
  - exactly one outbox message
  - completed idempotency record
- CI root cause from the first attempt was a stale `build_router` signature after API wiring; fixed by wiring the reject boundary into the router.
- Final CI runs 298 (push) and 299 (pull_request) both passed on Python 3.12 and 3.13.

## Verification

PASS — CI run #299: both Python 3.12 and 3.13 jobs succeeded, including Alembic lifecycle/checks and full pytest.

## Locked semantics preserved

- `DecisionMade != DecisionApproved`.
- Rejection is distinct from cancellation/failure.
- Authorization is enforced explicitly.
- Idempotency replay does not duplicate audit/outbox side effects.
- HTTP remains outside transaction/repository internals.
- No merge performed.

## Next

Proceed to the next explicitly bounded Decision command/lifecycle proof after reviewing remaining command coverage and the current application boundary for consistency.
