# REVENUE BILLING LEAKAGE DESIGN GATE

## Status

**PROPOSED — scope locked, implementation not started.**

## Objective

Validate that the existing Decision Core generalizes to a third materially different business-risk case: REVENUE_BILLING_LEAKAGE.

This gate is validation, not architecture expansion.

## Target capability

REVENUE_BILLING_LEAKAGE

The slice represents a governed business decision caused by a discrepancy between delivered/contracted commercial value and billed or collectible revenue.

## In scope

- New case type: REVENUE_BILLING_LEAKAGE.
- Controlled synthetic billing dataset.
- Evidence for contracted value, delivered value, billed value, and relevant period/context.
- Analysis findings using FACT, INFERENCE, and optionally HYPOTHESIS.
- At least two materially different decision options.
- Existing decision and approval boundaries.
- One governed remediation action and action execution.
- Expected and observed commercial outcome.
- Deterministic verification and closure.
- Existing tenant isolation, idempotency, audit, outbox, correlation, and optimistic-concurrency contracts.
- PostgreSQL integration coverage.
- Architecture tests and supported-Python CI.

## Explicitly out of scope

- New architectural layers.
- Generic billing/revenue rules engine.
- ERP/CRM/accounting integrations.
- Automated approval or autonomous execution.
- AI/agents.
- General accounting ledger implementation.
- Multi-currency accounting engine.
- Event sourcing.
- Microservices.
- Decision Memory projection.

## Design constraints

1. Reuse the existing DecisionCase → Evidence → Analysis → Options → Decision → Approval → Action → Execution → Outcome → Verification lifecycle.
2. Do not introduce revenue-specific behavior into generic infrastructure merely to make the test pass.
3. Keep business rules in domain/application policy.
4. Evidence remains immutable.
5. Analysis classification remains explicit.
6. Decision and approval remain separate.
7. Action execution remains distinct from business outcome.
8. Verification must deterministically control closure.
9. Tenant isolation and idempotency semantics remain unchanged.
10. Any architectural limitation must be documented as a GAP before changing architecture.

## Acceptance criteria

The gate can pass only when PostgreSQL integration demonstrates:

- REVENUE_BILLING_LEAKAGE reaches CLOSED through the existing lifecycle.
- Commercial evidence can be represented without changing the Evidence abstraction.
- Analysis can express the leakage finding without changing the Analysis abstraction.
- At least two materially different options can be represented without changing the Decision Core abstraction.
- Existing decision/approval authority boundaries remain intact.
- Action execution remains separate from commercial outcome.
- Deterministic verification controls closure.
- Tenant isolation remains enforced.
- Idempotent replay does not duplicate business records.
- Audit/outbox/correlation semantics remain unchanged for successful commands.
- Stale writes use the existing concurrency contract.
- No new architectural layer is required.
- Supported-Python CI and PostgreSQL migration checks pass.

## Implementation order

1. TDD RED: define REVENUE_BILLING_LEAKAGE acceptance tests.
2. Prove existing Case/Evidence/Analysis/Option/Decision abstractions are sufficient.
3. Add only minimum domain/application behavior if a concrete invariant requires it.
4. Add persistence/API coverage only where existing contracts require it.
5. Add one PostgreSQL end-to-end scenario.
6. Run architecture and CI verification.
7. Record PASS or GAP from evidence.

## Exit conditions

**PASS:** REVENUE_BILLING_LEAKAGE works without architectural change.

**GAP:** a concrete reusable-domain limitation is demonstrated and documented before any architecture change.

**FAIL:** unapproved architectural changes are introduced to make the slice work.
