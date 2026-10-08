# Authorization Model Design Gate

## Status

**INITIAL TENANT-SCOPED RBAC SLICE VERIFIED IN CI — OPERATIONAL-POLICY CLOSURE REMAINS OPEN.**

The product owner approved Option B. The implementation now includes actor lifecycle, tenant memberships, role/permission grants, membership-scoped role assignments, and a fail-closed SQLAlchemy adapter. Runtime composition uses this adapter by default while allowing an explicit replacement. Migration 0011 backfills actor rows but deliberately creates no memberships or role assignments.

## Non-negotiable invariants

- Authentication and authorization are separate.
- Every protected command checks permission against the authenticated actor, tenant, permission, and resource.
- A caller cannot choose actor or tenant IDs through request bodies or headers.
- Tenant membership must be checked server-side and cannot be inferred solely from a valid JWT tenant claim.
- Unknown actor, missing/inactive membership, missing permission, policy-store failure, and ambiguous policy must deny by default.
- Cross-tenant resource IDs must not authorize an action.
- Approval policy is separate from ordinary command authorization; permission to submit a decision does not imply approval authority.
- Authorization decisions must be auditable without logging bearer tokens or sensitive claims.
- No public endpoint may create or modify identity mappings, memberships, role assignments, or permissions until a trusted provisioning/admin model is designed.

## Options

| Option | Benefits | Costs / risks | Fit |
|---|---|---|---|
| A. Explicit injected policy adapter only | Smallest scope; keeps policy external; avoids premature schema | Runtime cannot be independently deployed until a real adapter is provided; configuration is deployment-specific | Good if an existing enterprise IAM/policy service is already chosen |
| B. Tenant-scoped RBAC in Decision OS | Clear server-side actor membership, role assignment, permission checks, and auditability; practical for initial SaaS | Requires actor/membership/role/permission schema, provisioning, cache/revocation policy, and policy tests | **Recommended default for the initial standalone multi-tenant product**, while keeping the port replaceable |
| C. Full ABAC/policy engine | Flexible resource attributes, separation of duties, and complex approval rules | Higher operational and reasoning complexity; harder to validate before real policies exist | Defer until real product requirements demonstrate need |

## Recommended minimal RBAC contract (Option B)

1. `actors`: internal actor UUID, lifecycle state; external identity records point to this actor rather than an arbitrary unreferenced UUID.
2. `tenant_memberships`: actor UUID + tenant UUID + active/revoked state; unique per actor/tenant pair.
3. `roles` and `role_permissions`: stable role and permission identifiers; permission values align with the application `Permission` enum or a validated versioned mapping.
4. `membership_role_assignments`: role assignment scoped to a tenant membership, with active state and optional audit metadata.
5. `SQLAlchemyAuthorizationAdapter.require`: resolve active membership, role assignments, and required permission for the requested tenant. Deny if any required record is absent or inactive.
6. Resource ownership/scope checks remain in the application command/domain boundary; a role grant never bypasses tenant-scoped resource loading.
7. Seed/provisioning is an explicit trusted administrative operation. No default allow-all role and no self-service privilege escalation.
8. Permission/role changes must be auditable. Cache decisions only after a revocation/expiry strategy is explicitly designed; initial adapter should query the authoritative store.

## Implemented initial role matrix

- `tenant_admin`: all current command permissions; highly privileged and must only be assigned through a trusted administrative process.
- `decision_author`: create/triage cases, start analysis, submit options, await decision, create evidence, and add analysis.
- `approver`: make, approve, or reject decisions.
- `operator`: create/start actions, update/reconcile execution, create/verify outcomes.
- `read_only_reviewer`: no command permissions; read APIs keep their own tenant-scoped query contracts.

The initial permissions are tenant-wide. Role separation does not yet prevent the same actor from holding author and approver roles or approving their own case.

## Verification evidence

- [x] Unit tests: allowed grant, wrong tenant, missing permission, inactive actor/membership/assignment/role, and policy-store failure.
- [x] PostgreSQL integration: seeded role catalog, explicit grant succeeds, wrong tenant and missing permission are denied, and membership revocation takes effect.
- [x] Migration upgrade/downgrade/upgrade and `alembic check` pass.
- [x] CI Runs #959/#960 passed on Python 3.12 and 3.13 for commit `2ff6fc635ba6779e4d097fc49e82e3ab3ff7958e`; each run reports 182 passed tests.

## Remaining before PASS

- Trusted provisioning for identity mappings, memberships, and role assignments.
- Durable audit of authorization decisions and role/membership changes.
- Explicit separation-of-duties rules, including whether the same actor may author and approve a case.
- Decide whether permissions need to vary by case type.
- Deployment-specific OIDC issuer, audience, JWKS URL, and tenant claim.

## Dependencies

See `docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md` and `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`. Do not mark deployment authentication or runtime composition gates PASS merely because JWT validation succeeds.
