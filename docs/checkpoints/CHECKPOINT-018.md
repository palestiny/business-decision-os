# CHECKPOINT-018 — First HTTP API Contract

## Status

PASS — contract and unit proof committed

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

CI must confirm the complete repository suite after this checkpoint.

## Next Proof

Run the first end-to-end HTTP integration path against PostgreSQL and the real application reliability boundary, including durable idempotency replay and outbox creation.
