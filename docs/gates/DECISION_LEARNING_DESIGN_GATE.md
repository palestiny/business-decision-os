# DECISION LEARNING & HISTORY DESIGN GATE

## Status

**PASS — Decision History implemented and verified; durable Learning explicitly deferred pending a demonstrated business requirement.**

## Purpose

Stage 9 extends the verified Decision Memory foundation into a controlled history and learning layer. Its purpose is to preserve decision context, verified outcomes, and reusable organizational learning without making learning an autonomous authority.

## Core model

Decision History answers: **What happened, why was it decided, what action followed, and what was verified?**

Verified Learning answers: **What did we learn from a completed and verified decision?**

The initial implementation must distinguish four concepts:

1. **Historical fact** — authoritative data already recorded by Decision Core or its verified outcome chain.
2. **Verified outcome** — an outcome whose verification state is established by the domain.
3. **Learning** — an explicit, traceable organizational statement derived from verified decision/outcome evidence.
4. **Recommendation** — a future analysis output that may use historical learning but never becomes authority by itself.

Learning must reference its source decision/case and verification context. Learning is not a replacement for business truth.

## Architectural decision

Decision Core remains authoritative for current business state. Decision Memory remains the read/projection foundation. Stage 9 should reuse these boundaries rather than introduce a second transactional decision model.

Initial learning records should be persisted as explicit domain/application records only when there is a demonstrated need for durable organizational learning. A generic AI/vector/graph memory system is explicitly rejected for this stage.

Decision History is a query concern first. It should compose the existing tenant-scoped Decision Memory projection and authoritative identifiers rather than duplicate the full Decision Core aggregate.

## History contract

The initial history query should provide a tenant-scoped chronological decision narrative containing, where available:

- case identity/type/title/status;
- decision identity/status/rationale/decider;
- selected options;
- approval state;
- action and execution summary;
- expected and actual outcome summaries;
- verification result;
- source identifiers;
- authoritative/projection versions and projection state.

The contract must make missing lifecycle elements explicit rather than inventing them.

## Learning contract

A durable learning item, if created in the first implementation, must contain at minimum:

- tenant scope;
- source case and decision identifiers;
- learning statement;
- evidence/source references;
- verification reference/state;
- creation metadata;
- explicit status.

It must be auditable and traceable back to verified source context.

## Safety boundaries

- Learning cannot approve, execute, or close a decision.
- Recommendations cannot silently mutate learning or authoritative decision state.
- AI-generated content, if introduced later, must remain advisory until explicitly accepted through a human-controlled workflow.
- Cross-tenant learning is out of scope.
- Unverified outcomes must not be represented as verified learning.
- Historical records must not be rewritten to fit later learning.

## Rejected alternatives

- **AI-first memory:** rejected; product must remain useful without AI and business truth must remain in the domain.
- **Vector database as source of truth:** rejected; retrieval infrastructure is not authoritative business state.
- **Graph database:** deferred; no demonstrated requirement yet.
- **Event sourcing:** rejected for this stage; transactional outbox and projections are sufficient.
- **Separate Learning service/microservice:** rejected; modular monolith remains appropriate.
- **Generic rule/recommendation engine:** deferred until a concrete business use case requires it.

## Acceptance criteria for Stage 9

Before closing this gate, implementation must prove:

1. A completed decision can be retrieved as a coherent tenant-scoped history narrative.
2. History remains consistent with authoritative Decision Core state and existing Decision Memory semantics.
3. Verified outcome context is distinguishable from unverified or missing outcome data.
4. Tenant isolation is enforced.
5. Historical facts are immutable from the learning layer.
6. Any durable learning record is traceable to source decision/case and verification context.
7. Learning cannot act as decision authority.
8. The implementation does not require new external infrastructure.
9. Supported-Python and PostgreSQL CI pass.
10. The first implementation does not introduce AI, vector search, graph storage, event sourcing, or microservices.

## Implementation order

1. TDD RED for Decision History query contract.
2. Reuse the existing Decision Memory read model and tenant boundary.
3. Add only the smallest domain/application contract required for history.
4. Add verified-learning persistence only if the tests demonstrate a real durable requirement.
5. Add tenant-isolation and immutability tests.
6. Add PostgreSQL integration coverage.
7. Run full CI.
8. Close the gate only after all acceptance criteria are evidenced.

## Verification evidence

### Decision History implementation
- TDD RED history contract: commit `ec131913e997c5608100923410540323f6bd98c1`.
- History API implementation reuses the tenant-scoped Decision Memory reader; no second transactional decision model was introduced: commit `8378b2f2eaadc96bee8d02e1708b13d7d95b71d2`.
- Supported-Python CI passed after the implementation: CI Run #772.
- PostgreSQL integration coverage verifies the real reader/API path and tenant isolation: commit `1184749599a1b76a31f8f45d45aca8e9f25a108c`, CI Run #774.
- Verified versus unverified/missing outcome context is explicitly preserved: commit `f5a0eadd2cbdab2c0438adb1914cd8e6e46e997d`.
- Latest CI for the verification test passed: CI Run #776 (`37617676754`).

### Learning boundary decision
No durable Learning record was introduced because the implemented history contract does not demonstrate a concrete requirement for persisted organizational learning yet. This is intentional and follows the gate's implementation order.

Therefore:
- historical facts remain sourced from Decision Core / Decision Memory and the History API exposes them read-only;
- there is no Learning persistence path capable of mutating historical facts;
- there is no recommendation or learning authority path;
- durable learning traceability is **N/A for this implementation slice**, rather than being satisfied by an artificial learning model.

The next Learning implementation requires a concrete business use case that demonstrates why a durable learning record is necessary. It must reopen this gate's learning criteria before persistence is added.

## Gate decision

**PASS — History slice closed.**

Decision History is verified and may serve as the controlled historical query surface. Durable organizational Learning remains explicitly deferred and must not be introduced merely to increase Stage 9 feature count.