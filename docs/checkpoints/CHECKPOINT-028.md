# CHECKPOINT-028 — Business Outcome & Verification

Status: IN PROGRESS — implementation complete, CI verification pending.

## Scope
- ExpectedOutcome domain and persistence
- ActualOutcome domain and persistence
- Deterministic Verification
- Outcome authority permissions
- Outcome reliability boundaries with idempotency, audit, and outbox
- Case lifecycle: OUTCOME_PENDING → VERIFYING → CLOSED
- Inconclusive verification remains VERIFYING and permits later verification retry
- HTTP API wiring for expected outcome, actual outcome, and verification

## Verified by inspection
- Alembic revision `0005_business_outcomes` is present and correctly chained after `0004_action_execution`.
- SQLAlchemy models and repositories are registered in the unit-of-work.
- Reliability boundaries use the shared transactional executor.
- Verification updates ActualOutcome truth state and closes a deterministically resolved case.

## Pending proof
- GitHub CI on the latest branch head must pass on Python 3.12 and 3.13.
- PostgreSQL integration test must prove persistence, replay, and single audit/outbox side effects.

## Open design item
Outcome numeric persistence currently uses string storage with Decimal-to-float reconstruction. This preserves the current schema without widening the gate, but precision semantics for financial/metric values should be revisited before production-grade metric modeling.
