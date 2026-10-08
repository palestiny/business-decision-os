# Trusted Authorization Provisioning Design Gate

## Status

**OPEN — CHOOSE A TRUSTED PROVISIONING PATH BEFORE IMPLEMENTATION.**

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
2. Support explicit operations to provision an external identity + membership + role assignment, list the effective grant for verification, and revoke a membership or role assignment. Do not implement arbitrary permission editing in the first slice.
3. Require the target tenant to exist and require explicit issuer, subject, tenant key, and role key. Accept an optional existing actor UUID only when linking an already-provisioned actor is an intentional operator action; otherwise create a new actor.
4. Validate the role against the seeded active role catalog. Reject unknown/inactive roles and conflicting existing identity mappings. Do not infer or create tenants.
5. Use one database transaction for all changes in a single provisioning operation.
6. Add a durable append-only authorization administration audit record in the same transaction, recording operator identity/source, operation, target actor/tenant, role, timestamp, and correlation/operation ID; never store tokens or secrets.
7. Provide dry-run output that lists intended changes without mutating the database. Require an explicit confirmation flag for writes.
8. Keep the CLI unavailable through the public API and document its least-privilege database/runtime access requirements.
9. Test idempotent repeat, conflicting mapping, unknown tenant/role, rollback on audit failure, revoke effect on the next authorization check, and cross-tenant isolation using PostgreSQL integration tests.

## Decisions still required

- Approve the offline CLI/job approach, or select A/C.
- Decide whether one external subject may be linked to the same internal actor across multiple tenants; initial safe default is no automatic linking, with explicit operator-supplied actor ID for intentional linking.
- Confirm whether initial Tenant Admin assignment requires a second-person review. Recommended: not in the first CLI, but all grants are explicitly audited and access to the command is tightly controlled.
- Decide whether an author may approve their own case. RBAC role separation alone does not prevent one actor holding both roles; approval separation-of-duties must be enforced in the application policy before this is treated as complete.

## Acceptance criteria

- No public provisioning route exists.
- Dry-run performs no writes; write mode requires explicit confirmation.
- Unknown tenant, role, issuer/subject mapping conflicts, and invalid actor references fail closed.
- Provisioning and its audit entry commit or roll back together.
- Identical retry is safe; conflicting retry is rejected.
- Revoked membership/assignment is denied by the next authorization check.
- Unit and PostgreSQL integration tests pass; migrations pass upgrade/downgrade/upgrade and alembic check.
- CI passes on Python 3.12 and 3.13.
- Documentation describes the operator trust boundary and recovery procedure.

## Dependencies

- docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md
- docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md
- docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md

Do not claim deployment readiness until provisioning, durable authorization administration audit, separation-of-duties policy, and deployment-specific OIDC configuration are verified.
