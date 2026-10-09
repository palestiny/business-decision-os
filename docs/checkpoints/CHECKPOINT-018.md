# CHECKPOINT-018 — First HTTP API Contract

## Status

PASS — HTTP create-case contract and runtime verification

## Verified

The first HTTP command boundary is defined for POST /api/v1/decision-cases.

Proof covers:
- request validation;
- required idempotency key;
- authenticated actor/tenant identity supplied through a principal boundary;
- correlation ID generation;
- correlation ID validation;
- correlation ID propagation to the reliability boundary;
- stable success response DTO;
- authentication error mapping;
- authorization error mapping;
- idempotency conflict mapping;
- request-in-progress mapping;
- domain conflict mapping;
- policy-unavailable mapping;
- unexpected-error sanitization.

## Architectural Guardrails

- HTTP does not own transactions.
- HTTP does not access repositories.
- HTTP does not accept tenant_id or actor_id from the request body.
- HTTP delegates idempotency semantics to the existing reliability boundary.
- HTTP does not expose domain objects directly.
- Internal exception details are not returned.
- Concrete authentication implementation remains an explicit composition concern.

## Evidence

tests/unit/application/test_api_contract.py
tests/unit/application/test_api_error_mapping.py
tests/integration/test_http_api_postgres.py

CI run #230 verified the HTTP integration path on Python 3.12 and 3.13. Alembic lifecycle/checks and the full pytest suite passed. The PostgreSQL-backed integration proof therefore has runtime verification.

## Runtime Evidence

CI run #230 (`36468174073`) passed on both Python 3.12 and 3.13. The jobs completed:
- Alembic upgrade/downgrade/upgrade lifecycle;
- Alembic current --check-heads;
- Alembic check;
- full pytest suite.

The HTTP integration test covers the real PostgreSQL reliability boundary, idempotency replay, durable case persistence, audit creation, and outbox creation.

## Next Proof

Add the next HTTP command boundary: POST /api/v1/decision-cases/{id}/triage, preserving the same API/application/reliability separation.
