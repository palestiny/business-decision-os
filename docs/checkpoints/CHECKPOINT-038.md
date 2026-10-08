# CHECKPOINT-038 — Runtime Composition First Slice

## Status
**Runtime composition and OIDC wiring are CI-verified; tenant-scoped RBAC is implemented in code and awaiting verification. Runtime gate remains open.**

## Delivered
- Added a runtime composition root that requires an explicit database URL, authorization adapter, and authenticated PrincipalProvider.
- Engine and Session factory are process-scoped; each create-case execution uses a short-lived Session.
- The UnitOfWork, handler, idempotency, audit, and outbox adapters for create-case share one Session/transaction.
- The work-queue reader creates and closes a Session per query, including exceptional query exit.
- PostgreSQL HTTP integration creates a Decision Case and verifies it appears once in the same tenant's work queue; a second tenant's queue cannot see it.
- CI Runs #844/#845 passed on Python 3.12 and 3.13 for commit 3e8a1ced033c8f0e97f2a130bd4b6cce169b116f.
- Concurrent command executions use distinct Sessions and close both contexts; CI Runs #854/#855 passed on Python 3.12 and 3.13 for commit f753c655f437c2e24e9de48fbf079ba1de7b7874.
- PostgreSQL integration verifies rollback after an Outbox write failure; CI Runs #862/#863 passed for commit dcccaf2816479f20613993058231f99ee3fbc05a.
- PostgreSQL-backed overlapping HTTP create requests both return 201 and persist; CI Runs #870/#871 passed on Python 3.12 and 3.13 for commit 191d3fcae473eecb710f786053e142eb605e7dc0.

## Authentication adapter progress
- Added OIDCJWTPrincipalProvider using PyJWT/JWKS, fixed RS256, explicit issuer/audience/JWKS/tenant claim, bounded clock skew, and an external identity resolver contract.
- Added fail-fast environment settings: OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL, OIDC_TENANT_CLAIM, and optional bounded OIDC_CLOCK_SKEW_SECONDS.
- Added external_identity_mappings SQLAlchemy model and Alembic revision 0010_external_identity_mappings. It maps the verified issuer/subject/tenant_key tuple to internal actor and tenant UUIDs; active mappings only resolve and tenant references are constrained.
- Added a Session-scoped SQLAlchemyExternalIdentityResolver and unit coverage for exact matching, inactive/unknown identities, and duplicate keys.
- Runtime composition now automatically builds the configured OIDC provider and database resolver when no provider is injected; missing OIDC environment configuration fails startup and disposes the engine. Added unit and PostgreSQL HTTP tests for invalid-signature and valid-but-unmapped tokens. CI Runs #938/#939 passed on Python 3.12 and 3.13 for commit `6a136b38bb4218e39742cfa8063c3050bc8ba705`; both jobs report 174 passed tests, and migration upgrade/downgrade/upgrade plus `alembic check` passed.
- Initial OIDC adapter suite passed CI #890/#891 on Python 3.12 and 3.13: https://github.com/palestiny/business-decision-os/actions/runs/37857658649 and https://github.com/palestiny/business-decision-os/actions/runs/37857662934.

## Tenant-scoped RBAC implementation added (pending CI)
- Added actor lifecycle, unique actor/tenant memberships, role catalog, role permissions, and membership-scoped role assignments.
- Migration `0011_tenant_scoped_rbac` backfills actors for existing identity mappings and deliberately creates no memberships or role assignments.
- Added fail-closed `SQLAlchemyAuthorizationAdapter`; runtime uses it by default while allowing explicit adapter injection.
- Initial roles: Tenant Admin, Decision Author, Approver, Operator, Read-only Reviewer. Unit tests cover grants, wrong tenant, missing permissions, inactive records, and policy-store failure.

## Remaining before gate closure
1. Verify migration upgrade/downgrade/upgrade, `alembic check`, and RBAC tests in CI on Python 3.12/3.13.
2. Establish trusted provisioning for identity mappings, memberships, and role assignments; no public provisioning endpoint exists.
3. Decide durable authorization audit and separation-of-duties rules, including whether an author may approve the same case.
4. Configure deployment OIDC issuer, audience, JWKS URL, and tenant claim.
5. Compose further command routes only after their authorization, transaction, and lifecycle dependencies are explicitly wired.
6. Add product-facing queue usability and operator workflow validation.

## Decision
Do not label this production-ready and do not mark the runtime gate PASS yet. Runtime composition's create-case/work-queue slice and OIDC runtime wiring are CI-verified. RBAC is implemented but its new CI run is pending; do not claim production readiness until RBAC verification, trusted provisioning, authorization auditing, separation-of-duties, and deployment configuration are complete.
