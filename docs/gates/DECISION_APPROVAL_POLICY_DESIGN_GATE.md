# Decision Approval Policy Design Gate

## Status

**OPTION A IMPLEMENTED — CI VERIFICATION IN PROGRESS; OPERATIONAL GATES REMAIN OPEN.**

The product owner approved Option A. Runtime composition now uses `RequireApprovalForEveryDecisionPolicy` by default and mounts `POST /api/v1/decision-cases/{case_id}/decision`; every decision requires independent approval and stores a stable policy identifier. An explicitly injected `PolicyEvaluatorPort` can replace the default for a reviewed deployment-specific policy. CI Runs #1096/#1097 are verifying this implementation on Python 3.12 and 3.13.

Four-eyes enforcement is implemented separately. Whenever approval is required, the approver must differ from both the case creator and decision maker; legacy cases without creator attribution fail closed.

## Invariants

- Approval-required status comes from an explicit policy evaluation, not from the caller, request body, RBAC role, or UI.
- The decision stores whether approval was required and the policy identifiers used for that evaluation.
- If policy evaluation is unavailable or ambiguous, decision submission fails closed; it must not silently fall back to `approval_required=false`.
- Approval authorization and four-eyes separation-of-duties remain separate checks.
- Policy changes must be versioned and auditable before the system supports live editing.
- AI may provide evidence or recommendations, but cannot authoritatively waive approval requirements.

## Options

| Option | Rule | Benefits | Costs / risks |
|---|---|---|---|
| A. Approval required for every decision in the first release | Every submitted decision enters `AWAITING_APPROVAL`; only a separately authorized, four-eyes-compliant actor may approve | Safest simple default; no hidden approval bypass; straightforward to explain and test | More operational friction; even low-risk decisions require a second person |
| B. Explicit case-type policy matrix | A versioned policy maps each supported case type to required/optional approval | Better workflow fit while remaining deterministic | Requires the owner to define risk classes, defaults for new case types, and change governance |
| C. Threshold/attribute policy | Approval depends on impact, confidence, financial exposure, tenant configuration, or combinations | Flexible for enterprise usage | Requires trusted, validated attributes, policy administration, explainability, and more extensive testing |
| D. External policy service | Decision OS delegates to an explicitly configured policy service | Supports centralized enterprise governance | Adds deployment dependency, availability contract, identity mapping, and operational complexity |

## Recommendation

**Start with Option A for the first deployable workflow**, but keep `PolicyEvaluatorPort` replaceable. This prevents an implicit no-approval default while the product lacks a settled case-risk matrix. After real users establish risk categories, evolve to Option B with explicit versioned policy records. Do not add threshold-based policy (Option C) until the required impact attributes and their trusted sources are defined.

## Implementation boundary

If Option A is approved:

1. Add a small deterministic evaluator with a stable policy identifier and `required=true`.
2. Wire it as the default runtime policy evaluator, while preserving explicit injection for tests or enterprise deployments.
3. Ensure evaluator errors fail closed and are surfaced through the normal error contract.
4. Verify a submitted decision always enters `AWAITING_APPROVAL` in the default runtime.
5. Verify the decision's policy identifier and approval-required flag persist and survive idempotent replay.
6. Verify the separate four-eyes rule still blocks creator/decision-maker self-approval.
7. Keep the runtime gate open until deployment identity configuration and operational security controls are verified.

## Decision

- [x] **Option A approved:** every decision requires approval in the first release.
- [x] Stable policy identifier is persisted with the decision; idempotent replay returns the same approval-required flag and policy identifier.
- [x] Runtime keeps explicit policy injection available for a reviewed replacement policy.
- [x] Unit tests cover deterministic approval requirement and stable policy identifier.
- [x] PostgreSQL runtime integration exercises the default policy rather than injecting a test policy.
- [ ] CI verification and migration checks for the final commit must pass before marking this gate PASS.
- [ ] Runtime/deployment security gates remain separate and open.

## Dependencies

- `docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md`
- `docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md`
- `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`

Do not mark runtime composition PASS until the default approval policy is explicit and verified.
