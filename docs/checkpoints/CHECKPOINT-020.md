# CHECKPOINT-020 — Make Decision HTTP Contract

## Status

PASS — Make Decision HTTP contract and PostgreSQL runtime verification

## Verified

The Make Decision command boundary is implemented at:

POST /api/v1/decision-cases/{id}/decision

Proof covers:
- authenticated actor/tenant identity;
- required idempotency key;
- stable decision success response;
- selected option validation through the application boundary;
- authoritative policy evaluation;
- approval-required decision state;
- captured authority snapshot;
- idempotency replay;
- durable decision persistence;
- durable audit creation;
- durable outbox creation;
- atomic PostgreSQL persistence;
- fail-closed behavior when policy evaluation is unavailable.

## Architectural Guardrails

- HTTP does not own transactions.
- HTTP does not access repositories directly.
- HTTP does not accept tenant_id or actor_id from the request body.
- HTTP delegates idempotency semantics to the reliability boundary.
- Command handling remains transaction-neutral.
- Policy evaluation remains authoritative and is not caller-controlled.
- Policy evaluation failure prevents decision creation and case mutation.
- Reliability owns audit, outbox, idempotency completion, and commit.
- Replay preserves the original business response data while each HTTP request retains its own correlation ID.

## Evidence

tests/unit/application/test_api_contract.py
tests/unit/application/test_make_decision_command.py
tests/integration/test_postgres_persistence.py

The PostgreSQL integration proof executes the real FastAPI route against the real Make Decision reliability boundary and PostgreSQL persistence, then replays the same idempotency key. A separate integration proof verifies that policy unavailability leaves the case and decision state unchanged.

## Runtime Evidence

CI run #269 (36478644140) passed on Python 3.12 and 3.13.

The jobs completed successfully:
- Alembic upgrade/downgrade/upgrade lifecycle;
- Alembic current --check-heads;
- Alembic check;
- full pytest suite.

The Make Decision integration proof verified:
- decision persisted with approval_required = true;
- selected option persisted;
- case transitioned to AWAITING_APPROVAL;
- exactly one audit event;
- exactly one outbox message;
- idempotency record COMPLETED;
- replay returned identical business data with a distinct correlation ID;
- unavailable policy produced no decision and no case transition.

## Next Proof

Add the HTTP Approve Decision command boundary, preserving explicit approval semantics, authorization, idempotency, audit, outbox, and transaction ownership at the reliability boundary.
