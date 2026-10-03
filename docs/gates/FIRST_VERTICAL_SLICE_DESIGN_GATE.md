# FIRST VERTICAL SLICE DESIGN GATE

## Status

**PASS — implementation scope and acceptance criteria locked.**

This gate defines the first end-to-end product slice for `PROJECT_MARGIN_RISK`. It is a product-validation slice, not a claim of commercial validation.

## Objective

Prove that Decision OS can take a concrete project-margin risk from a detected case through:

`Signal → Case → Evidence → Analysis → Options → Decision → Approval → Action → Execution → Outcome → Verification → Closure`

The slice must demonstrate the complete closed loop without AI, external provider integrations, or autonomous authority.

## Scope

### In scope

- Case type: `PROJECT_MARGIN_RISK`.
- Synthetic controlled project dataset.
- Structured Evidence records.
- Structured Analysis findings with explicit fact/inference/hypothesis distinction.
- Existing Options, Decision, Approval, Action, ActionExecution, Outcome, and Verification foundations.
- PostgreSQL persistence.
- Tenant isolation.
- Idempotency.
- Optimistic concurrency.
- Append-only audit.
- Transactional outbox.
- HTTP contract for the vertical slice.
- Deterministic verification.
- Full integration test proving the lifecycle and replay behavior.

### Out of scope

- AI-generated analysis or recommendations.
- Real ERP/PSA/CRM integrations.
- External action providers.
- Automated approval.
- Autonomous execution.
- Decision Memory as a source of truth.
- General-purpose metric expression language.
- Multi-metric outcome orchestration.
- Microservices or graph storage.

## Domain rules

1. Evidence is immutable. A changed source produces new evidence.
2. Evidence is not automatically an analysis conclusion.
3. Analysis explicitly distinguishes fact, inference, and hypothesis.
4. AI is not required for the first slice.
5. A decision cannot be made before required analysis/options are present.
6. Approval remains distinct from decision.
7. Action creation does not execute the action.
8. Execution success does not imply business success.
9. Outcome verification is deterministic in the first slice.
10. UNKNOWN/INCONCLUSIVE evidence is preserved rather than converted into success or failure.
11. Case closure occurs only after the required outcome verification succeeds or fails deterministically.
12. Every command crossing a reliability boundary has idempotency, audit, outbox, and correlation semantics consistent with the existing contract.

## Minimal PROJECT_MARGIN_RISK scenario

The controlled dataset must contain enough facts to support a realistic margin-risk decision, including:

- project identifier/context;
- planned revenue/cost/margin;
- current or observed revenue/cost/margin evidence;
- period/time context;
- source and capture metadata;
- at least one deterministic analysis finding;
- at least two decision options with materially different responses;
- one selected option;
- an approval decision where policy requires it;
- one internal action execution;
- an expected margin outcome;
- an observed margin result;
- deterministic verification and closure.

The exact numeric values are test data, not product assumptions.

## Acceptance criteria

The gate is considered implemented only when PostgreSQL integration proves:

- the complete lifecycle reaches `CLOSED`;
- evidence remains immutable;
- analysis preserves fact/inference/hypothesis semantics;
- tenant boundaries are enforced;
- invalid lifecycle commands fail without partial persistence;
- idempotent replay does not duplicate business records;
- audit and outbox side effects occur exactly once per successful command;
- optimistic concurrency rejects stale writes;
- action execution remains distinct from business outcome;
- verification determines closure from explicit expected/observed values;
- CI passes on supported Python versions with PostgreSQL and migration checks.

## Next implementation order

1. Evidence domain + persistence + command boundary.
2. Analysis finding domain + persistence + command boundary.
3. Wire both into the existing lifecycle.
4. Add PROJECT_MARGIN_RISK controlled dataset and end-to-end integration test.
5. Verify CI.
6. Record the next checkpoint only after CI evidence exists.

## Architectural constraint

Do not introduce a new architectural layer merely to complete this slice. Extend the existing modular-monolith boundaries and ports/adapters.

