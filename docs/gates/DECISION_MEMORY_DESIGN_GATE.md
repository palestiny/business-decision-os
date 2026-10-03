# DECISION MEMORY PROJECTION DESIGN GATE

## Status

**DESIGN-LOCKED — consistency model selected; implementation not started.**

## Decision

ADR-016 selects an **outbox-triggered, authoritative-state projection**. The projector treats each outbox record as an aggregate-change notification, then reloads current authoritative Decision Core state. The outbox payload is not interpreted as business truth.

Decision Core remains authoritative. Decision Memory is a tenant-scoped, eventually consistent, rebuildable read model.

## Projection

Initial record: tenant_id, case_id, case_type, case_title, case_status, decision_id, selected options, rationale, decision status, decided_by, approval status, action status, expected/observed outcome summaries, verification status, authoritative case version, source IDs, projected_at, and explicit projection state/lag metadata.

## Reliability

- projection identity is tenant + case;
- duplicate delivery reloads current authoritative state;
- out-of-order delivery reloads current authoritative state;
- projection failure cannot roll back a committed business decision;
- rebuild is from authoritative state, not historical outbox payloads;
- tenant isolation is mandatory;
- projection never validates or authorizes commands.

## Out of scope

AI summaries, embeddings, graph storage, cross-tenant analytics, event sourcing, external brokers, and replacing the transactional outbox.

## Acceptance criteria

A completed decision is projected and queried; tenant isolation is proven; duplicate/out-of-order delivery is harmless; projection failure does not corrupt authoritative state; source references and authoritative version are retained; rebuild/reconciliation works; projection lag is explicit; PostgreSQL and supported-Python CI pass; no external infrastructure is introduced.

## Next implementation order

1. Projection schema/model and source/version contract.
2. Authoritative-state projector.
3. Outbox-trigger adapter.
4. Query/read contract.
5. TDD RED for duplicate, ordering, failure, rebuild, tenant isolation.
6. PostgreSQL integration.
7. CI verification.
