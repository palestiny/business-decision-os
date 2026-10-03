# ADR-010: Command Reliability Boundary

## Status

Accepted

## Context

Decision commands mutate durable business state and will eventually be exposed through APIs, integrations, retries, and asynchronous workflows. A successful domain transition is not sufficient if a client retries the same request, an audit record is lost, or an external event is published before the database transaction commits.

The platform already has ports and persistence models for idempotency, audit, and transactional outbox. Their transactional semantics must be explicit before they are wired into command handlers.

## Decision

1. Reliability is enforced at the **application command boundary**, not inside domain entities.
2. Every externally retryable command uses an idempotency key scoped by `tenant_id + operation + key`.
3. The request hash is compared on reuse:
   - same key + same hash + completed request: return the stored response;
   - same key + different hash: raise `IdempotencyConflict`;
   - same key + same hash + active request: raise `RequestInProgress`.
4. Reservation occurs before the command side effect.
5. The idempotency record, domain mutation, audit event, and outbox message are committed in the **same database transaction**.
6. Audit events are append-only. They record actor, tenant, command/action, entity, timestamp, and correlation ID.
7. Outbox records are durable facts produced by the transaction. External publication occurs only after commit and is retried independently.
8. A failed transaction must not leave a completed idempotency record, audit event, or outbox message behind.
9. The outbox is not an event-sourcing store; it exists to reliably bridge committed state to asynchronous consumers.
10. Response serialization for idempotency is an application concern and must be deterministic. The first implementation may store a serialized response body plus status.
11. The Unit of Work remains the atomic transaction owner. The reliability boundary orchestrates ports but must not introduce a second transaction mechanism.

## Application boundary

The intended flow is:

`request -> validate/hash -> reserve idempotency -> authorize/policy -> domain command -> persist mutation -> audit -> outbox -> complete idempotency -> commit -> publish asynchronously`

The exact ordering of `complete idempotency` versus transaction commit is implementation-defined, but both must participate in the same transaction.

## Trade-offs

### Application command boundary

**Pros**
- Keeps domain pure.
- Makes retries and audit consistent across commands.
- Avoids duplicating reliability logic in every domain entity.

**Cons**
- Requires a reusable command execution abstraction.
- Requires deterministic request/response serialization.

### Handler-local reliability

**Pros**
- Small initial code change.

**Cons**
- Duplicates semantics across handlers.
- Easy to apply one guarantee to one command and forget another.
- Makes API and integration behavior inconsistent.

Handler-local reliability is rejected as the default architecture.

### Full event sourcing

**Pros**
- Strong historical reconstruction model.

**Cons**
- Significantly increases complexity.
- Is not required to guarantee idempotency, audit, or reliable integration publication.

Full event sourcing is out of scope for v0.1.

## Initial implementation scope

Prove the boundary with one command first, preferably `CreateDecisionCase`, then generalize only after integration verification.

The proof must demonstrate:

- duplicate same request does not create a second case;
- same key with a different request is rejected;
- audit and outbox are committed atomically with the case;
- rollback removes all reliability records and the domain mutation;
- outbox publication is not required for transaction success.

## Verification requirements

Before API exposure:

- idempotency uniqueness is tenant-scoped;
- request-hash conflict is deterministic;
- in-progress duplicate is distinguishable from conflict;
- audit is append-only;
- outbox rows survive process failure after commit;
- domain state, audit, outbox, and completed idempotency state share one transaction;
- external publication happens after commit.

## Consequence

The existing ports/models are retained. The next implementation step is a small application-level execution boundary plus PostgreSQL adapters and integration tests, rather than embedding reliability semantics directly in `DecisionCase` or `Decision`.
