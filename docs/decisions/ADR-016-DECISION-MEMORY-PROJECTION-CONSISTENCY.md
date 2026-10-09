# ADR-016 — Decision Memory Projection Consistency

## Status

**ACCEPTED**

## Context

Decision Memory needs a query-oriented historical surface while Decision Core remains the authoritative source of business truth.

The existing transactional outbox provides tenant_id, correlation_id, topic, aggregate_type, aggregate_id, occurred_at, payload, and publication state. The current payload is command-result-oriented and is not defined as a stable domain-event schema.

## Decision

Use an **outbox-triggered, authoritative-state projection** for the first Decision Memory implementation.

The projector consumes an outbox record as a notification that an aggregate changed. It then loads the authoritative current state from the Decision Core and upserts the tenant-scoped Decision Memory record.

The outbox payload is not interpreted as the source of business truth.

### Consistency

- Authoritative command transaction commits first.
- Projection update happens after the authoritative transaction is committed.
- Projection is eventually consistent.
- A projection failure must not roll back the committed business decision.

### Idempotency and ordering

Projection updates are keyed by authoritative tenant + case identity. Duplicate delivery reloads current authoritative state and produces the same projection. Older delivery after newer delivery also reloads current authoritative state, so it cannot restore stale command-result data.

A projection record stores authoritative version metadata so reconciliation can detect lagging updates.

### Rebuild

The projection can be rebuilt from authoritative Decision Core records without relying on historical outbox payloads. Rebuild is explicit and safe to repeat.

## Alternatives considered

### Transactional projection

Rejected for the first implementation because it would couple every decision command to the read model and make projection failures part of the business transaction.

### Stable domain-event contract

Deferred. The current outbox can trigger projection without interpreting payload semantics. A formal domain-event contract should be introduced only if another concrete capability requires semantic event consumption.

### Message broker

Rejected. No demonstrated scale or deployment requirement currently justifies external messaging infrastructure.

### Event sourcing

Rejected. Decision Core remains stateful and authoritative; a projection does not require event sourcing.

## Consequences

Positive: preserves Decision Core authority, uses existing outbox infrastructure, supports duplicate/out-of-order delivery safely, allows rebuild, and avoids new infrastructure.

Trade-offs: Decision Memory is eventually consistent; query results can temporarily lag authoritative state; projector/reconciliation become operational responsibilities.

## Guardrails

- tenant isolation is mandatory;
- projection must never validate or authorize business commands;
- projection failures must be observable;
- source IDs and authoritative version must be retained;
- tests must cover duplicate, out-of-order, failure, rebuild, and tenant isolation.
