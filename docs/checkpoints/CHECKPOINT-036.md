# CHECKPOINT-036

## Status

**DESIGN-LOCKED — Decision Memory consistency model selected.**

## Design review result

The existing outbox was inspected. It carries aggregate identity and operational metadata, but its payload is command-result-oriented rather than a stable domain-event contract. The first Decision Memory implementation will therefore not interpret the payload as business truth.

## Locked architecture

Use an **outbox-triggered, authoritative-state projection**:

1. authoritative command commits;
2. transactional outbox records the aggregate change;
3. projector receives the outbox record;
4. projector reloads authoritative current state;
5. projector upserts the tenant-scoped read model.

This provides eventual consistency, safe duplicate/out-of-order handling, and rebuildability without introducing a broker or event-sourcing architecture.

## Guardrails

- Decision Core remains authoritative.
- Projection failures cannot roll back committed decisions.
- Duplicate/out-of-order delivery must be harmless.
- Rebuild uses authoritative state.
- Tenant isolation is mandatory.
- AI, vector search, graph storage, brokers, and event sourcing remain out of scope.

## ADR

docs/decisions/ADR-016-DECISION-MEMORY-PROJECTION-CONSISTENCY.md

## Next action

Start TDD RED for the projection contract and implement the smallest PostgreSQL read model.
