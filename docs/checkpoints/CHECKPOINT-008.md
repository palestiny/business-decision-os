# CHECKPOINT-008

## Scope

Authority and reliability boundaries before persistence.

## Completed

- Defined authorization port and explicit permissions.
- Defined policy evaluator port returning explicit approval requirements.
- Defined idempotency reservation/completion port.
- Distinguished idempotency conflict from an in-progress request.
- Defined append-only audit port.
- Defined transactional outbox message port.
- Added boundary tests for the new contracts.

## Locked semantics

- Permission denial is distinct from domain validation.
- Policy evaluation determines whether approval is required; the Decision entity does not own policy lookup.
- Idempotency uniqueness is tenant + operation + key.
- Audit is append-only.
- Outbox messages participate in the same transaction as business state.
- External side effects must not be performed directly inside a request transaction.

## Next

Implement persistence models/migrations for DecisionCase, Decision, Option, idempotency, audit and outbox, then add repository and Unit of Work integration tests.
