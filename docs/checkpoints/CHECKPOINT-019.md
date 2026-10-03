# CHECKPOINT-019 — Triage HTTP Contract

## Status

PASS — Triage HTTP contract and PostgreSQL runtime verification

## Verified

The second HTTP command boundary is defined for POST /api/v1/decision-cases/{id}/triage.

Proof covers:
- authenticated actor/tenant identity;
- required idempotency key;
- stable success response DTO;
- triage state transition;
- optimistic version increment;
- idempotency replay;
- durable audit creation;
- durable outbox creation;
- atomic PostgreSQL persistence.

## Architectural Guardrails

- HTTP does not own transactions.
- HTTP does not access repositories.
- HTTP does not accept tenant_id or actor_id from the request body.
- HTTP delegates idempotency semantics to the reliability boundary.
- Command handling remains transaction-neutral.
- Reliability owns audit, outbox, idempotency completion, and commit.
- Replay preserves the original case data while each HTTP request retains its own correlation ID.

## Evidence

tests/unit/application/test_api_contract.py
tests/integration/test_postgres_persistence.py

The PostgreSQL integration proof executes the real FastAPI route against the real reliability boundary and PostgreSQL persistence, then replays the same idempotency key.

## Runtime Evidence

CI run #244 (36475912297) passed on Python 3.12 and 3.13.

The jobs completed successfully:
- Alembic upgrade/downgrade/upgrade lifecycle;
- Alembic current --check-heads;
- Alembic check;
- full pytest suite.

The verified replay produced identical business response data, exactly one TriageCase audit event, exactly one decision-case.triaged outbox message, and a COMPLETED idempotency record.

## Next Proof

Add the HTTP Make Decision command boundary, preserving authoritative policy evaluation, fail-closed approval semantics, idempotency, audit, outbox, and transaction ownership at the reliability boundary.
