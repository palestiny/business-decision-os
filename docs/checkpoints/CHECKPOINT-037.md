# CHECKPOINT-037 — Human Decision Work Queue

## Status
**Stage 10 read-only queue slice PASS; runtime composition remains deferred.**

## Delivered
- Added a tenant-scoped `DecisionWorkQueueReader` application port.
- Added PostgreSQL reader based on authoritative case, decision, and action records.
- Added `GET /api/v1/decision-work-queue` through the existing FastAPI application factory.
- Classified work into REVIEW_CASE, MAKE_DECISION, APPROVE_DECISION, EXECUTE_ACTION, and REVIEW_OUTCOME.
- Deterministic ordering uses attention priority then case UUID.
- Approved cases appear as EXECUTE_ACTION only when a tenant-matching action is READY.
- Added unit and PostgreSQL integration tests for mapping, ordering, tenant isolation, and ready-action eligibility.

## Verification
- CI Run #806 succeeded on commit `870995158a1fae799241408cf39b95bae52e2e49`.
- Run: https://github.com/palestiny/business-decision-os/actions/runs/37850119985

## Known limitation
No deployment composition root exists in the current repository. The API factory accepts the reader via dependency injection, but a future runtime entry point must create and manage database sessions with appropriate request lifecycle. Do not inject a global long-lived SQLAlchemy Session.

The queue reads authoritative Decision Core tables directly, so `projection_state` is null by design for this slice; it is not a statement about Decision Memory freshness.

## Next step
Design the runtime composition boundary before introducing a deployable entry point; then validate session lifecycle, authentication wiring, database configuration, and the work queue in the actual application startup path.
