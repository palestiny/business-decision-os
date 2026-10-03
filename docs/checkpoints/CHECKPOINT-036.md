# CHECKPOINT-036

## Status

**DESIGN-LOCKED — Decision Memory projection design gate opened.**

## Previous milestone

Stage 7 abstraction validation is complete.

Validated cases:

- PROJECT_MARGIN_RISK
- RESOURCE_CAPACITY_RISK
- REVENUE_BILLING_LEAKAGE

The Decision Core handled the materially different cases without architecture expansion.

## Why this is next

The product thesis identifies Decision Memory as a potential long-term product advantage, while the current system has not yet implemented a query-oriented historical decision surface.

This checkpoint therefore moves the project from abstraction validation toward product value.

## Scope

The next gate will define and validate a tenant-scoped, rebuildable Decision Memory read model.

The read model must not become a source of truth for business decisions.

## Locked constraints

- Decision Core remains authoritative.
- Projection is read-oriented.
- Tenant isolation is mandatory.
- Projection updates must be idempotent.
- Projection failures must not roll back committed business decisions.
- Rebuild/reconciliation must be possible.
- AI, embeddings, graph storage, and external brokers are out of scope unless a concrete requirement proves otherwise.
- Existing transactional outbox must be evaluated before introducing any new event abstraction.

## Next action

Run the Decision Memory design review:

1. inspect existing outbox semantics;
2. determine whether the current payload contract is sufficient;
3. compare transactional versus outbox-driven projection;
4. select the smallest architecture that satisfies the query and reliability requirements;
5. write the Decision Memory design gate;
6. only then start TDD RED.
