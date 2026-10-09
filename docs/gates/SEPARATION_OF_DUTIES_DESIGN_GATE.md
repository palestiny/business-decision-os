# Separation-of-Duties Design Gate

## Status

**PASS — OPTION B IMPLEMENTED AND VERIFIED IN CI.**

The product owner approved Option B. New cases persist `created_by`; approved decisions persist `approved_by` and `approved_at`. The approval handler checks `APPROVE_DECISION` authorization first, then independently rejects the case creator, decision maker, and legacy cases with missing creator attribution. A tenant-admin role does not bypass these checks.

## Security objective

For decisions that require approval, the system must prove who created the case, who made the decision, and who approved it. A valid permission grant is necessary but not sufficient to bypass separation-of-duties policy.

## Options

| Option | Rule | Benefits | Risks / costs |
|---|---|---|---|
| A. Decision maker differs from approver | Enforce decided_by != approved_by | Smallest schema and behavior change | Case creator may still approve if a different actor made the decision |
| B. Case creator and decision maker both differ from approver | Enforce created_by != approved_by and decided_by != approved_by; persist approval actor/time | Strongest simple four-eyes model; clear audit evidence | Adds creator/approval fields, migration and legacy-data policy |
| C. Configurable tenant policy | Per-tenant/case-type rules and exceptions | Flexible for enterprise workflows | Requires policy administration, exception governance and more complex tests |

## Recommendation

Choose Option B as the safe default for the initial Decision OS product:

1. Persist DecisionCase.created_by for new cases.
2. Persist Decision.approved_by and approved_at when approval succeeds.
3. For an approval-required decision, deny approval if the current actor is either the case creator or decision maker, even if the actor has APPROVE_DECISION and tenant_admin.
4. Keep APPROVE_DECISION authorization and separation-of-duties validation as separate checks.
5. Fail closed when creator attribution is missing on a legacy case. Do not infer the creator from the current caller. A trusted, audited backfill/exception process must be designed if existing pending approvals need migration.
6. Add unit and PostgreSQL integration coverage for same creator, same decision maker, distinct approver, missing legacy attribution, wrong tenant, and transaction rollback.
7. Do not add a general-purpose override in the first slice. If business needs require exceptions, design an explicit dual-control exception later.

## Acceptance criteria

- [x] Product owner approved Option B.
- [x] New case creator and decision maker are persisted.
- [x] Successful approval records actor and timestamp durably.
- [x] Same-creator and same-decision-maker approvals are denied independently of RBAC role grants.
- [x] Missing creator attribution fails closed for approval-required cases.
- [x] Unit and PostgreSQL tests verify authorization and separation-of-duties are independent controls.
- [x] PostgreSQL migration upgrade/downgrade/upgrade and Alembic check pass.
- [x] CI Runs #995/#996 passed on Python 3.12 and 3.13; 200 tests passed per run.

## Implementation and verification evidence

- Added Alembic migration `0013_separation_of_duties` for nullable legacy-compatible `decision_cases.created_by`, `decisions.approved_by`, and `decisions.approved_at`.
- Create-case command persists authenticated actor attribution; approval writes approver ID and UTC timestamp in the same decision transaction.
- Same creator, same decision maker, missing legacy attribution, and distinct approver are covered by unit and PostgreSQL integration tests. The existing HTTP approval replay test verifies the approver and timestamp survive persistence and idempotent replay.
- CI Runs #995/#996 passed at commit `d293535e0fc0ac9bbe71a738867a03906a05195c`; each Python version reports 200 passed tests, and migration lifecycle plus `alembic check` passed.
- Legacy cases without creator attribution intentionally remain unapprovable. No inferred creator, generic override, or unaudited backfill was added.

## Dependencies

- docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md
- docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md
- docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md

Do not mark authorization or runtime gates PASS until this policy is decided and verified.
