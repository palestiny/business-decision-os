# Trusted Authorization Provisioning Design Gate

## Status

**OPTION B IMPLEMENTED AND CI-VERIFIED — SEPARATION-OF-DUTIES AND DEPLOYMENT POLICY REMAIN OPEN.**

Tenant-scoped RBAC is implemented and CI-verified. The runtime intentionally grants no access merely because an OIDC identity resolves: an active actor, active tenant membership, active role assignment, and explicit permission grant are all required. Migration 0011 seeds the role catalog but creates no memberships or role assignments.

This gate decides how an authorized operator creates and revokes identity mappings, tenant memberships, and role assignments without exposing a public privilege-escalation endpoint.

## Security invariants

- Provisioning is never available to an unauthenticated or ordinary tenant user.
- No default membership, default tenant-admin grant, or implicit role assignment.
- Provisioning changes are validated and committed atomically; partial actor/mapping/membership/assignment state must not be left behind.
- The issuer, subject, tenant key, internal tenant ID, and requested role are explicit inputs and validated against existing records.
- Existing identity mappings are never silently reassigned to another actor or tenant.
- Repeating an identical provisioning request is safe; conflicting repeats fail clearly.
- Revocation takes effect on the next authorization check; no authorization cache is introduced.
- Secret bearer tokens and full token claims are never accepted as provisioning input or logged.
- Every grant/revoke must be attributable to a trusted operator and produce durable audit evidence.
- Tenant Admin is a highly privileged role and requires an explicit role grant; no first-user auto-admin rule.

## Options

| Option | Benefits | Risks / costs | Fit |
|---|---|---|---|
| A. Hand-run SQL only | No application surface; minimal code | Error-prone, weak validation/idempotency, poor operator feedback and audit discipline | Emergency recovery only |
| B. Offline administrative CLI/job | No public HTTP privilege endpoint; validates input, supports dry-run, idempotency, transaction boundaries, and structured audit | Requires secure operator access to deployment environment and credential handling | **Recommended first provisioning mechanism** |
| C. Private administrative API | Better future operator UX and identity-provider integration | Requires a trusted admin identity, admin authorization, network boundary, abuse protection, and audit before it is safe | Defer until operator/admin product exists |

## Recommended first implementation (Option B)

1. Add a dedicated administrative command entry point, separate from the public FastAPI router.
2. Support explicit operations to provision an external identity + membership + role assignment, inspect the effective grant, and revoke a membership or role assignment. Do not implement arbitrary permission editing in the first slice.
3. Require the target tenant to exist and require explicit issuer, subject, tenant key, and role key. Accept an optional existing actor UUID only when linking an already-provisioned actor is an intentional operator action; otherwise create a new actor.
4. Validate the role against the seeded active role catalog. Reject unknown/inactive roles and conflicting existing identity mappings. Do not infer or create tenants.
5. Use one database transaction for all changes in a single provisioning operation.
6. Add a durable append-only authorization administration audit record in the same transaction, recording operator identity/source, operation, target actor/tenant, role, timestamp, and correlation/operation ID; never store tokens or secrets.
7. Provide dry-run output that lists intended changes without mutating the database. Require an explicit confirmation flag for writes.
8. Keep the CLI unavailable through the public API and document its least-privilege database/runtime access requirements.
9. Test idempotent repeat, conflicting mapping, unknown tenant/role, rollback on audit failure, revoke effect on the next authorization check, and cross-tenant isolation using PostgreSQL integration tests.

## Decisions still required

- [x] Product owner approved Option B: offline administrative CLI/job.
- Decide whether one external subject may be linked to the same internal actor across multiple tenants; initial safe default is no automatic linking, with explicit operator-supplied actor ID for intentional linking.
- Confirm whether initial Tenant Admin assignment requires a second-person review. Recommended: not in the first CLI, but all grants are explicitly audited and access to the command is tightly controlled.
- Decide and enforce case-creator/decision-maker separation from the approver; see `docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md`. RBAC role separation alone does not prevent one actor holding both roles.

## Initial implementation delivered

- Added `decision-os-admin` offline entry point; it is not mounted on FastAPI.
- Provision, membership revoke, and role-assignment revoke default to dry-run. Writes require `--confirm`; `show-identity` is read-only and reports effective roles/permissions.
- Provisioning requires explicit issuer, subject, tenant key, tenant ID, role, and operator; tenant is not inferred or created.
- Provisioning validates active role/actor/membership state, rejects conflicting identity mappings, and applies mapping + membership + role assignment + audit in one transaction.
- Added `authorization_admin_audit` append-only-by-application table and migration 0012; no public endpoint or arbitrary permission-edit command is exposed.
- Dry-run planning is read-only. Repeated matching grants are idempotent and recorded; revoked/inactive records require explicit recovery rather than being silently reactivated.
- CI Run #983 passed on Python 3.12 and 3.13 at commit `7533424a1dcacf4921261f3a94c245dc5a62847d`: 193 tests passed per version; Alembic migration lifecycle and `alembic check` passed.

### Operator examples (PowerShell)

```powershell
$env:SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://..."

# Plan only; does not write anything
 decision-os-admin --database-url $env:SQLALCHEMY_DATABASE_URL provision --issuer "https://issuer.example" --subject "provider-subject" --tenant-key "tenant-key" --tenant-id "00000000-0000-0000-0000-000000000000" --role "read_only_reviewer" --operator "change-ticket:CHG-123"

# Repeat the same command with --confirm only after reviewing the plan
# Add --confirm before the operator argument to commit the grant.

# Inspect the effective grant without mutating state
decision-os-admin --database-url $env:SQLALCHEMY_DATABASE_URL show-identity --issuer "https://issuer.example" --subject "provider-subject" --tenant-key "tenant-key"

# Revoke a role assignment; dry-run first, then add --confirm
decision-os-admin --database-url $env:SQLALCHEMY_DATABASE_URL revoke-role --assignment-id "00000000-0000-0000-0000-000000000000" --operator "change-ticket:CHG-124"
```

Run the CLI only from a trusted administrative environment with tightly scoped database access. Apply migrations separately before provisioning. The examples use placeholders, not valid credentials or production identifiers.

## Acceptance criteria

- No public provisioning route exists.
- Dry-run performs no writes; write mode requires explicit confirmation.
- Unknown tenant, role, issuer/subject mapping conflicts, and invalid actor references fail closed.
- Provisioning and its audit entry commit or roll back together.
- Identical retry is safe; conflicting retry is rejected.
- Revoked membership/assignment is denied by the next authorization check.
- [x] Unit and PostgreSQL integration tests pass; migrations pass upgrade/downgrade/upgrade and alembic check (CI #983, 193 tests per Python version).
- [x] PostgreSQL verifies provision+audit atomicity, idempotent retry, conflict rejection, effective grant inspection, and revocation denial. Unit tests additionally verify rollback when audit insertion fails.
- [x] CI passes on Python 3.12 and 3.13.
- Documentation describes the operator trust boundary and recovery procedure.

## Dependencies

- docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md
- docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md
- docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md
- docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md

Do not claim deployment readiness until provisioning, durable authorization administration audit, separation-of-duties policy, and deployment-specific OIDC configuration are verified.
