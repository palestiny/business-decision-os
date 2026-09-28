# CHECKPOINT-021 — Approve Decision HTTP Contract

## Status

PASS — Approve Decision HTTP contract and PostgreSQL runtime verification

## Verified

The Approve Decision command boundary is implemented at:

POST /api/v1/decision-cases/{case_id}/decision/{decision_id}/approve

Proof covers:
- authenticated actor/tenant identity;
- required idempotency key;
- explicit APPROVE_DECISION authorization;
- explicit approval transition;
- decision persistence from AWAITING_APPROVAL to APPROVED;
- case transition to APPROVED;
- idempotency replay;
- durable audit creation;
- durable outbox creation;
- atomic PostgreSQL persistence.

## Architectural Guardrails

- HTTP does not own transactions.
- HTTP does not access repositories directly.
- HTTP does not accept tenant_id or actor_id from the request body.
- Authorization remains inside the application command boundary.
- Approval remains a first-class command and is not folded into Make Decision.
- Command handling remains transaction-neutral.
- Reliability owns audit, outbox, idempotency completion, and commit.
- Replay preserves business response data while each HTTP request retains its own correlation ID.

## Evidence

tests/unit/application/test_api_contract.py
tests/integration/test_postgres_persistence.py
src/decision_os/application/commands/approve_decision.py
src/decision_os/application/approve_decision_reliability.py

The PostgreSQL integration proof executes the real FastAPI route against the real Approve Decision reliability boundary and PostgreSQL persistence, then replays the same idempotency key.

## Runtime Evidence

CI run #285 (36479984354) passed on Python 3.12 and 3.13.

The jobs completed successfully:
- Alembic upgrade/downgrade/upgrade lifecycle;
- Alembic current --check-heads;
- Alembic check;
- full pytest suite.

The Approve Decision integration proof verified:
- decision transitioned to APPROVED;
- case transitioned from AWAITING_APPROVAL to APPROVED;
- exactly one ApproveDecision audit event;
- exactly one decision.approved outbox message;
- idempotency record COMPLETED;
- replay returned identical business data with a distinct correlation ID.

## Next Proof

Add the HTTP Reject Decision command boundary, preserving explicit rejection semantics, authorization, idempotency, audit, outbox, and transaction ownership at the reliability boundary.
