# DECISION MEMORY PROJECTION DESIGN GATE

## Status

**PASS — implementation, verification, and CI complete.**

## Decision

ADR-016 selects an **outbox-triggered, authoritative-state projection**. The projector treats each outbox record as an aggregate-change notification, then reloads current authoritative Decision Core state. The outbox payload is not interpreted as business truth.

Decision Core remains authoritative. Decision Memory is a tenant-scoped, eventually consistent, rebuildable read model.

## Projection

Implemented projection stores tenant_id, case_id, case metadata, decision state, selected options, rationale, approval status, action/outcome/verification summaries, source IDs, authoritative case version, projection lag metadata, and projected_at.

## Reliability

- projection identity is tenant + case;
- duplicate delivery reloads current authoritative state;
- out-of-order delivery reloads current authoritative state;
- projection failure does not corrupt or roll back the authoritative business state;
- rebuild reconstructs the projection from authoritative state;
- tenant isolation is enforced by the projection repository and API;
- projection never validates or authorizes commands;
- projection lag is explicit through notified_version, projected_version, authoritative_version, and state.

## Read / API

Implemented tenant-scoped Decision Memory read repository and:
GET /decision-cases/{case_id}/memory

The response exposes decision, action, outcome, verification, source references, and projection metadata including current/stale state and versions.

## Verification Evidence

- Projection unit/integration coverage for authoritative-state projection.
- Duplicate/out-of-order notification verification.
- Projection failure isolation.
- Rebuild verification.
- Explicit projection-lag verification.
- Tenant isolation verification.
- PostgreSQL read API integration coverage.
- Migration lifecycle and alembic check verification.
- CI Run **#762** (`37155367148`) succeeded on both Python **3.12** and **3.13**.
- CI executed PostgreSQL-backed migration lifecycle and full pytest suite.

## Out of scope

AI summaries, embeddings, graph storage, cross-tenant analytics, event sourcing, external brokers, and replacing the transactional outbox.

## Gate Decision

**PASS.**

Decision Memory now has a verified first implementation and read surface. The next work should be a controlled follow-up slice, not expansion of Decision Memory into event sourcing, a broker, or an ERP replacement.
