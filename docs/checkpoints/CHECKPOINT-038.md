# CHECKPOINT-038 — Runtime Composition First Slice

## Status
**Runtime composition through action uncertainty/reconciliation and verified outcomes is CI-verified, alongside OIDC/RBAC/provisioning/four-eyes controls. Runtime gate remains open for deployment and operational security controls.**

## Delivered
- Added a runtime composition root requiring a database URL; it defaults to database-backed fail-closed RBAC and configured OIDC/JWT identity validation unless explicit adapters are injected.
- Engine and Session factory are process-scoped; each create-case, triage-case, start-analysis, create-evidence, add-analysis-finding, and submit-options execution uses a short-lived Session.
- The UnitOfWork, handler, idempotency, audit, and outbox adapters for create-case, triage-case, start-analysis, create-evidence, add-analysis-finding, and submit-options share one Session/transaction per command.
- Runtime triage route persists status/version, preserves creator attribution on idempotent replay, propagates request correlation, and rejects cross-tenant case access. CI #1035 passed on Python 3.12/3.13 at commit `b65cfcb89dcd86cf510fe513a8880c2d933fa950`, with 206 tests per version and migration checks passing.
- Start-analysis is composed in the runtime and tested for persistence, `TRIAGED → ANALYZING`, idempotent replay, creator-attribution serialization, and correlation propagation. CI #1039 passed on Python 3.12/3.13 at commit `0b65866ede42b6f34dec28b9308b47d1b89ce9a4`, with 207 tests per version and migration checks passing.
- Create-evidence is composed in the runtime and verified along the create → triage → start-analysis → evidence path, including persistence and correlation propagation. CI Runs #1043/#1044 passed on Python 3.12/3.13 at commit `45ad57d8f5b598af32b49aa224cc70c51d0456f9`, with 208 tests per version and migration checks passing.
- Add-analysis-finding is composed after evidence creation; PostgreSQL integration checks that only existing same-case evidence can be referenced, that the finding persists, and that identical idempotent replay returns the same finding. CI Runs #1047/#1048 passed on Python 3.12/3.13 at commit `b43943673671a8affcd360feeb4d2a58f9733c9e`, with 208 tests per version and migration checks passing.
- Submit-options is composed after an evidence-backed finding. Its integration path verifies two options persist, the case transitions to `OPTIONS_READY` at version 3, and idempotent replay does not repeat the transition. CI Runs #1051/#1052 passed on Python 3.12/3.13 at commit `be9731824a6d24141b52ee132110ff2c33772188`, with 208 tests per version and migration checks passing.
- Await-decision is composed with request-scoped persistence, RBAC, idempotency, audit/outbox, and correlation. PostgreSQL verifies `OPTIONS_READY → AWAITING_DECISION`, version 4, replay, and persisted state. CI #1055/#1056 passed on Python 3.12/3.13 with 209 tests per version.
- Await-decision is composed with a request-scoped Session, UoW, RBAC, idempotency, audit, and outbox. PostgreSQL verifies `OPTIONS_READY → AWAITING_DECISION`, version 4, correlation ID, replay, and persisted state. CI #1055/#1056 passed on Python 3.12/3.13 with 209 tests per version and migration checks.
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

## Runtime execution uncertainty and outcome verification
- Composed mark-execution-unknown and reconciliation using a request-scoped Session/UoW, authorization, idempotency, audit/outbox, and correlation.
- PostgreSQL HTTP integration verifies `RUNNING → UNKNOWN`, keeps the action in `EXECUTING` until authoritative reconciliation, then transitions `UNKNOWN → SUCCEEDED`, action `EXECUTING → COMPLETED`, and case `EXECUTING → OUTCOME_PENDING`. Replay is stable and does not retry the external action.
- Composed create-expected-outcome, record-actual-outcome, and verify-outcome boundaries, each using one Session/transaction for the command handler, UoW, idempotency, audit, and outbox.
- PostgreSQL HTTP integration verifies expected/actual/verification persistence, idempotent replay, request correlation, and `OUTCOME_PENDING → CLOSED` after a passing verification.
- CI Runs #1087/#1088 passed on Python 3.12/3.13 at commit `688020042fcdaf6249f1e19b74dc12f37f56b9a2`: 218 tests passed per version; migration lifecycle and `alembic check` passed.

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

## Authorization decision audit implementation (CI-verified)
- Product owner approved Option B: durable PostgreSQL audit for each completed allow/deny decision.
- Added migration `0014_authorization_decision_audit`, model, indexes by tenant/time, actor/time, resource, and correlation ID.
- Authorization policy query and audit insertion share one short transaction; DENY is committed before `AuthorizationDenied` is raised. Audit or policy-store failure denies via `PolicyEvaluationUnavailable`.
- Read API authorization calls now attach request correlation IDs. Rows contain internal identifiers and bounded reason codes only, not bearer tokens or raw claims.
- Added unit tests for allow/deny persistence and fail-closed audit-write failure, plus PostgreSQL integration for durable attribution.
- CI Runs #1011/#1012 passed on Python 3.12 and 3.13 at commit `da4c67045073191df7307c88a2ea5f232b16cecc`; migration upgrade/downgrade/upgrade, `alembic current --check-heads`, `alembic check`, and pytest all passed.

## Audit retention/access policy decision (approved; operational evidence open)
- Product owner approved a 365-day searchable default; longer archive requires explicit deployment/customer policy and encryption/access controls.
- Product owner approved restricted security/operations audit access, with no public audit-query API; tenant admins never receive platform-wide audit access.
- Automatic deletion/cleanup remains disabled until legal-hold, archive, and active-investigation protections are designed and tested.
- Deployment-specific backup provider, encrypted PITR/retention, restore drill, RPO/RTO, and database role separation remain open; no production readiness is implied.
- See `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`.

## Default decision approval policy (implemented; final CI verification pending)
- Product owner approved Option A: every decision requires independent approval in the first release.
- Added `RequireApprovalForEveryDecisionPolicy` with stable policy ID `7f89d3e1-0f30-4f88-9c57-3bbf12c6a001`; runtime uses it when no `PolicyEvaluatorPort` override is injected.
- Make-decision is now composed by default. The PostgreSQL runtime integration path exercises the default policy and checks the policy ID survives idempotent replay.
- Explicit evaluator injection remains available for a reviewed case-type matrix or external policy service.
- CI Runs #1096/#1097 passed on Python 3.12/3.13 with 221 tests per version; migration lifecycle and Alembic checks passed. #1097 verifies persisted policy-ID stability across idempotent replay.

## Remaining before runtime/security gate closure
1. Operate provisioning only from a trusted environment and document production recovery/retention; implementation is CI-verified in `docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md`.
2. Command authorization correlation propagation is implemented and verified in CI #1023/#1024; no longer an open item.
3. Review any remaining direct/alternate authorization paths and define audit retention/access policy.
3. Configure deployment-specific OIDC issuer, audience, JWKS URL, and tenant claim.
4. Compose further command routes only after authorization, transaction, and lifecycle dependencies are explicitly wired. Complete-action-execution is composed and CI-verified in #1079/#1080; PostgreSQL verifies `RUNNING → SUCCEEDED`, action/case transitions, persistence, correlation, and replay. Next reliability work is unknown-outcome handling and reconciliation. Start-action is composed and CI-verified in #1075/#1076; PostgreSQL verifies attempt 1 RUNNING, case/action version transitions, and replay. Make-decision uses RequireApprovalForEveryDecisionPolicy by default, with explicit PolicyEvaluatorPort override supported; policy-ID persistence/replay verification passed in CI #1096/#1097. Approve-decision is now composed and PostgreSQL verifies distinct-approver four-eyes enforcement, `approved_by`/`approved_at` persistence, and replay. CI #1063/#1064 passed on Python 3.12/3.13 with migration checks. Reject-decision is composed with request-scoped persistence, RBAC, idempotency, audit/outbox, and correlation. PostgreSQL verifies `AWAITING_APPROVAL → REJECTED`, persisted state, and idempotent replay. CI #1067/#1068 passed on Python 3.12/3.13 with migration checks. Create-action is composed only after approval; PostgreSQL verifies READY state/version 1, case/decision linkage, persisted action, correlation, and replay. CI #1071/#1072 passed on Python 3.12/3.13 with migration checks.
5. Queue API bounded cursor pagination and filters are now implemented and CI-verified in CHECKPOINT-039; operator workflow usability and deployment/security operations remain open.
6. Validate product-facing queue usability and operator workflow.

## Decision
Do not label this production-ready or mark the runtime gate PASS yet. Runtime composition, OIDC wiring, RBAC, protected read routes, trusted provisioning implementation, and four-eyes approval are CI-verified. Trusted-environment operations, audit retention/access policy (see `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`), and deployment configuration remain open. Command-authorization correlation propagation is verified in CI Runs #1023/#1024 (204 tests per supported Python version); triage runtime composition is verified in CI #1035 (206 tests per supported Python version); start-analysis composition passed CI #1039 (207 tests per supported Python version).
