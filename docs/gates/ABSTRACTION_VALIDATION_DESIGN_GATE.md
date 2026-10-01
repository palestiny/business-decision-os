# ABSTRACTION VALIDATION DESIGN GATE

## Status

**PROPOSED — scope locked, implementation not started.**

## Objective

Validate that the existing Decision Core abstractions generalize to a second materially different business-risk case without architectural redesign.

## Target capability

RESOURCE_CAPACITY_RISK

The slice represents a capacity/capability shortage or overload that requires a governed business decision. It must reuse the existing DecisionCase → Evidence → Analysis → Options → Decision → Approval → Action → Execution → Outcome → Verification lifecycle.

## Why this gate exists

The first vertical slice proves the lifecycle for project-margin risk. The next step is not to add infrastructure or AI; it is to test whether the domain model remains reusable when the business facts and decision semantics change.

## In scope

- New case type: RESOURCE_CAPACITY_RISK.
- Controlled synthetic capacity dataset.
- Evidence records for capacity demand, available capacity, skills/capabilities, and relevant period context.
- Analysis findings preserving fact/inference/hypothesis semantics.
- At least two materially different decision options.
- Decision and approval using existing authority boundaries.
- One governed action and action execution.
- Expected and observed capacity outcome.
- Deterministic verification and closure.
- Existing tenant isolation, idempotency, audit, outbox, correlation, and optimistic-concurrency contracts.
- PostgreSQL integration coverage.
- Architecture tests and supported-Python CI.

## Explicitly out of scope

- New architectural layers.
- New persistence infrastructure unless an existing domain invariant cannot be represented safely.
- AI/agents.
- ERP/PSA integrations.
- Automated approval or autonomous execution.
- Generic resource scheduling/optimization engine.
- Multi-period optimization.
- Graph database.
- Microservices.
- Decision Memory projection.
- New observability infrastructure.

## Design constraints

1. Reuse existing lifecycle and reliability boundaries.
2. Do not copy PROJECT_MARGIN_RISK-specific behavior into generic infrastructure.
3. Business rules belong in domain/application policy, not HTTP handlers.
4. Evidence remains immutable.
5. Analysis must distinguish fact, inference, and hypothesis.
6. Decision and approval remain separate.
7. Action execution remains distinct from business outcome.
8. UNKNOWN/INCONCLUSIVE verification must remain explicit.
9. Tenant isolation and idempotency semantics must remain unchanged.
10. Any proposed architectural change requires a separate design decision rather than being silently introduced.

## Acceptance criteria

The gate can pass only when PostgreSQL integration demonstrates:

- RESOURCE_CAPACITY_RISK reaches CLOSED through the existing lifecycle.
- Evidence and analysis semantics remain valid.
- At least two options can be represented without changing the Decision Core abstraction.
- Tenant isolation remains enforced.
- Invalid lifecycle transitions fail atomically.
- Idempotent replay does not duplicate business records.
- Audit/outbox/correlation semantics remain exactly-once for successful commands.
- Stale writes fail with the existing concurrency contract.
- Action execution remains separate from business outcome.
- Deterministic verification controls closure.
- No new architectural layer is required.
- CI passes on supported Python versions with PostgreSQL and migration checks.

## Implementation order

1. TDD RED: define RESOURCE_CAPACITY_RISK domain acceptance tests.
2. Prove whether existing Case/Evidence/Analysis/Option/Decision abstractions are sufficient.
3. Add only the minimum domain/application behavior required.
4. Add persistence/API coverage where the existing contracts require it.
5. Add one end-to-end PostgreSQL scenario.
6. Run architecture and CI verification.
7. PASS or GAP the gate based on evidence.

## Exit conditions

**PASS:** second case type works without architectural change.

**GAP:** a concrete reusable-domain limitation is demonstrated; document it before changing architecture.

**FAIL:** the slice requires architectural changes that were not approved by a separate design decision.
