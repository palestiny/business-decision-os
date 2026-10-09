# CHECKPOINT-038 — Runtime Composition First Slice

## Status
**Runtime composition, OIDC wiring, tenant-scoped RBAC, permission-gated reads, trusted provisioning, and four-eyes approval are CI-verified. Runtime gate remains open for deployment and operational security controls.**

## Delivered
- Added a runtime composition root requiring a database URL; it defaults to database-backed fail-closed RBAC and configured OIDC/JWT identity validation unless explicit adapters are injected.
- Engine and Session factory are process-scoped; each create-case execution uses a short-lived Session.
- The UnitOfWork, handler, idempotency, audit, and outbox adapters for create-case share one Session/transaction.
- The work-queue reader creates and closes a Session per query, including exceptional query exit.
- PostgreSQL HTTP integration creates a Decision Case and verifies it appears once in the same tenant's work queue; a second tenant's queue cannot see it.
- CI Runs #844/#845 passed on Python 3.12 and 3.13 for commit 3e8a1ced033c8f0e97f2a130bd4b6cce169b116f.
- Concurrent command executions use distinct Sessions and close both contexts; CI Runs #854/#855 passed on Python 3.12 and 3.13 for commit f753c655f437c2e24e9de48fbf079ba1de7b7874.
- PostgreSQL integration verifies rollback after an Outbox write failure; CI Runs #862/#863 passed for commit dcccaf2816479f20613993058231f99ee3fbc05a.
- PostgreSQL-backed overlapping HTTP create requests both return 201 and persist; CI Runs #870/#871 passed on Python 3.12 and 3.13 for commit 191d3fcae473eecb710f786053e142eb605e7dc0.

## Authentication adapter
- Added OIDCJWTPrincipalProvider using PyJWT/JWKS, fixed RS256, explicit issuer/audience/JWKS/tenant claim, bounded clock skew, and an external identity resolver contract.
- Required environment settings: OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL, OIDC_TENANT_CLAIM; optional OIDC_CLOCK_SKEW_SECONDS is bounded.
- Added external_identity_mappings model and Alembic revision 0010_external_identity_mappings, with exact active mapping from issuer/subject/tenant key to internal actor and tenant UUIDs.
- Runtime automatically builds the configured OIDC provider and database resolver when no provider is injected. Missing OIDC configuration fails startup. CI Runs #938/#939 passed on Python 3.12 and 3.13 for commit 6a136b38bb4218e39742cfa8063c3050bc8ba705; both report 174 tests passed, with migration upgrade/downgrade/upgrade and alembic check passing.

## Tenant-scoped RBAC and read API enforcement
- Added actor lifecycle, unique actor/tenant memberships, role catalog, role permissions, and membership-scoped role assignments.
- Migration 0011 backfills actor rows for existing identity mappings and deliberately creates no memberships or role assignments.
- Added fail-closed SQLAlchemyAuthorizationAdapter; runtime uses it by default while allowing explicit adapter injection.
- Seeded roles: Tenant Admin, Decision Author, Approver, Operator, Read-only Reviewer. Read-only Reviewer receives only VIEW_DECISION_HISTORY, VIEW_DECISION_MEMORY, and VIEW_DECISION_WORK_QUEUE.
- History, memory, and work-queue routes require their corresponding permissions; enabling these readers without an AuthorizationPort fails app composition.
- Unit tests cover grants, wrong tenant, missing permissions, inactive actor/membership/assignment/role, policy-store failure, and protected read route denial.
- PostgreSQL integration verifies seeded roles, explicit grants, wrong-tenant denial, missing-permission denial, membership revocation, and read-only reviewer restrictions.
- CI Runs #959/#960 passed for the initial RBAC slice; latest read-route enforcement passed CI #967/#968 on Python 3.12 and 3.13 at commit ca8e5272aaa8fa90d491e2b62677e109181f3bdc, with 184 tests per run and migration checks passing.

## Trusted provisioning implementation (CI-verified)
- Product owner approved the offline CLI/job approach; no public HTTP provisioning route is added.
- Added `decision-os-admin` with provision, show-identity, revoke-membership, and revoke-role operations; dry-run is default and writes require `--confirm`.
- Added migration 0012 and `authorization_admin_audit`; provisioning/membership/assignment changes and audit records share one DB transaction.
- The provisioner validates tenant, active role, actor references, mapping conflicts, and inactive membership/assignment states; no tenant or default admin is auto-created.
- CI #983 passed on Python 3.12/3.13 at commit `7533424a1dcacf4921261f3a94c245dc5a62847d`, with 193 tests per version and migration lifecycle/Alembic checks passing.

## Four-eyes approval implementation (CI-verified)
- Migration `0013_separation_of_duties` adds case creator and approval actor/time attribution while retaining nullable creator attribution for legacy rows.
- Approval checks the `APPROVE_DECISION` permission independently, then denies approval by the case creator, decision maker, or any actor when a legacy case has no creator attribution. Tenant Admin cannot bypass the rule.
- Unit and PostgreSQL integration tests cover same-creator, same-decision-maker, missing legacy attribution, and distinct-approver persistence/replay.
- CI Runs #995/#996 passed on Python 3.12/3.13 at commit `d293535e0fc0ac9bbe71a738867a03906a05195c`, with 200 tests per run and migration lifecycle/Alembic checks passing.

## Authorization decision audit implementation (CI pending)
- Product owner approved Option B: durable PostgreSQL audit for each completed allow/deny decision.
- Added migration `0014_authorization_decision_audit`, model, indexes by tenant/time, actor/time, resource, and correlation ID.
- Authorization policy query and audit insertion share one short transaction; DENY is committed before `AuthorizationDenied` is raised. Audit or policy-store failure denies via `PolicyEvaluationUnavailable`.
- Read API authorization calls now attach request correlation IDs. Rows contain internal identifiers and bounded reason codes only, not bearer tokens or raw claims.
- Added unit tests for allow/deny persistence and fail-closed audit-write failure, plus PostgreSQL integration for durable attribution. CI and migration verification are pending commit `07abb63e22fa1427100902f9c0160a7bf6809308`.

## Remaining before runtime/security gate closure
1. Operate provisioning only from a trusted environment and document production recovery/retention; implementation is CI-verified in `docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md`.
2. Authorization-decision audit implementation is committed and awaiting CI; review any remaining direct/alternate authorization paths after CI.
3. Configure deployment-specific OIDC issuer, audience, JWKS URL, and tenant claim.
4. Compose additional command routes only after authorization, transaction, and lifecycle dependencies are explicitly wired.
5. Validate product-facing queue usability and operator workflow.

## Decision
Do not label this production-ready or mark the runtime gate PASS yet. Runtime composition, OIDC wiring, RBAC, protected read routes, trusted provisioning implementation, and four-eyes approval are CI-verified. Trusted-environment operations, broader authorization-decision auditing, and deployment configuration remain open.
