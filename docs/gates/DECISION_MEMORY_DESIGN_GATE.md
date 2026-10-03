# DECISION MEMORY PROJECTION DESIGN GATE

## Status

**DESIGN-LOCKED — Decision Memory projection gate opened.**

## Objective

Define a read-oriented Decision Memory projection that makes completed and in-progress decisions discoverable without becoming a second source of business truth.

This gate is a product/read-model capability, not a rewrite of the Decision Core.

## Problem

The Decision Core currently preserves governed decision state, evidence, analysis, approval, execution, outcomes, verification, audit, and outbox records. That supports operational correctness, but users also need to answer historical questions such as:

- What decisions have we made?
- Why was a decision made?
- What evidence and analysis supported it?
- Who decided and approved it?
- What action was taken?
- What outcome was expected and observed?
- Was the decision verified?
- What happened across similar cases?

The projection must make this information queryable without moving authority away from the domain model.

## Target capability

A tenant-scoped **Decision Memory read model** containing denormalized decision-history views suitable for API/query consumption.

The projection is explicitly:

- read-only from the product's decision-authority perspective;
- derived from authoritative domain/application state;
- rebuildable;
- eventually consistent where asynchronous projection is used;
- tenant isolated;
- auditable through source references;
- not a replacement for DecisionCase, Evidence, Decision, Outcome, or Audit as sources of truth.

## Proposed projection boundary

Initial projection record:

- tenant_id
- case_id
- case_type
- case_title
- case_status
- decision_id
- selected option identifiers/titles
- decision rationale
- decision status
- decided_by
- approval status
- action type/status
- expected outcome summary
- observed outcome summary
- verification status
- created/decision/verification timestamps
- correlation/source references needed to trace back to authoritative records

Do not copy every domain table into the projection. The projection exists to answer decision-history queries, not to mirror the database.

## Consistency model

The initial design must explicitly choose between:

1. **Transactional projection**
   - update the read model in the same database transaction as the command.
   - simpler consistency.
   - tighter coupling between write and read models.

2. **Outbox-driven projection**
   - publish committed outbox messages and update the projection asynchronously.
   - preserves write/read separation and scales better.
   - introduces eventual consistency and requires replay/rebuild semantics.

The design review must decide which model is justified by current requirements. Do not introduce a message broker or distributed infrastructure merely to implement the first projection.

## Event contract constraint

The current transactional outbox exists, but its current payloads must not automatically be treated as a stable domain-event contract.

Before implementation, verify whether existing outbox messages contain sufficient stable semantic information for projection. If not, document the smallest reusable event-contract GAP first.

Do not introduce generic domain events solely because a projection would be easier with them.

## Required query scenarios

The first projection must support at least:

1. list decisions for a tenant with filtering by case type/status;
2. retrieve one decision history by case ID;
3. inspect rationale, selected options, approval, action, outcome, and verification status;
4. identify the authoritative source IDs for the displayed information;
5. distinguish current operational state from historical decision context.

Search, ranking, AI similarity, embeddings, graph storage, and semantic recommendation are out of scope.

## Reliability requirements

- Tenant isolation is mandatory.
- Projection updates must be idempotent.
- Duplicate/out-of-order delivery must not corrupt the read model.
- A projection failure must not roll back an already committed business decision.
- Projection lag must be observable through explicit state/metadata.
- Rebuild from authoritative state must be possible.
- Projection records must never become an authority for command validation.

## Explicitly out of scope

- AI-generated memory or summaries.
- Vector database / embeddings.
- Graph database.
- Autonomous recommendations.
- Cross-tenant analytics.
- Event sourcing.
- Replacing the transactional outbox.
- Message broker adoption without a demonstrated requirement.
- Changing domain authority boundaries.
- Replacing existing audit history.

## Acceptance criteria

The gate can pass only when:

- the projection has a documented source-of-truth model;
- tenant isolation is proven;
- a completed decision can be projected and queried;
- the projection survives duplicate delivery;
- projection failure does not corrupt the authoritative transaction;
- source references allow the read model to be traced back to authoritative records;
- rebuild/reconciliation semantics are defined and tested;
- stale/lagging projection state is explicitly represented;
- no new infrastructure is introduced without a demonstrated requirement;
- supported-Python CI and PostgreSQL migration checks pass.

## Design constraint

The first implementation must remain inside the existing modular monolith and PostgreSQL strategy unless a concrete requirement proves that a separate infrastructure boundary is necessary.

## Exit conditions

**PASS:** Decision Memory is implemented as a rebuildable, tenant-scoped read model without weakening Decision Core authority.

**GAP:** a concrete reusable limitation is demonstrated and documented before architecture expansion.

**FAIL:** the projection becomes an alternative source of truth or introduces unapproved infrastructure merely for convenience.
