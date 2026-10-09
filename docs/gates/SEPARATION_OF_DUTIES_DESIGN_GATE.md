# Separation-of-Duties Design Gate

## Status

**OPEN — RECOMMENDED POLICY: THE APPROVER MUST DIFFER FROM BOTH THE CASE CREATOR AND DECISION MAKER.**

The current RBAC adapter can grant both author and approver roles to one actor. Decision records decided_by, but DecisionCase does not persist its creator and approval does not persist approved_by. Therefore role names alone do not establish a four-eyes control.

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

- [ ] Product owner approves Option B or chooses A/C.
- [ ] New case creator and decision maker are persisted.
- [ ] Successful approval records actor and timestamp durably.
- [ ] Same-creator and same-decision-maker approvals are denied, including for Tenant Admin.
- [ ] Missing creator attribution fails closed for approval-required cases.
- [ ] Tests verify authorization and separation-of-duties are independent controls.
- [ ] PostgreSQL migration lifecycle and Alembic check pass.
- [ ] CI passes on Python 3.12 and 3.13.

## Dependencies

- docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md
- docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md
- docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md

Do not mark authorization or runtime gates PASS until this policy is decided and verified.
