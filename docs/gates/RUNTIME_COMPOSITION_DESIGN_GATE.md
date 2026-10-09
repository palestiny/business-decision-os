# Runtime Composition Design Gate

## Purpose

Define the production composition boundary for the existing Decision Core API before adding a deployment entry point.

## Current state

- The API factory accepts already-constructed command boundaries and readers.
- Persistence adapters currently hold SQLAlchemy Session instances.
- A runtime composition root now builds an Engine and Session factory, composes the create-case command boundary, and provides a session-factory-backed work-queue reader.
- The create-case UnitOfWork, idempotency, audit, and outbox adapters share one use-case-scoped Session.
- The queue reader opens and closes a Session per query.
- The runtime requires an explicit database URL and defaults to a database-backed, fail-closed RBAC AuthorizationPort; an explicit alternative adapter may be injected. If a PrincipalProvider is not injected, it builds the configured OIDC/JWT provider and database-backed identity resolver. The runtime now composes create-case, triage-case, start-analysis, create-evidence, add-analysis-finding, and submit-options with request/use-case-scoped Sessions.
- Authentication is delegated to an explicitly injected PrincipalProvider; the default provider rejects requests without an authenticated principal.

An OIDC/JWT PrincipalProvider adapter now exists at `src/decision_os/infrastructure/authentication/oidc_jwt.py`. Runtime composition now uses it when no test/provider override is injected, with a database-backed resolver for server-provisioned external identity mappings. The mapping model and Alembic migration are implemented; CI verification for the current resolver/runtime-auth changes passed in Runs #938/#939 on Python 3.12 and 3.13; deployment-specific settings and further command composition remain open. See `docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md`.

## Decisions

1. A SQLAlchemy Engine and session factory are process-scoped; a Session is never shared between HTTP requests.
2. Each command execution receives a request/use-case-scoped Session. Its UnitOfWork, repositories, idempotency adapter, audit adapter, and outbox adapter must share that same Session and transaction.
3. Read-only query adapters open/use/close a Session within the query request and must not retain a Session globally.
4. The runtime must require SQLALCHEMY_DATABASE_URL and fail startup clearly if it is missing.
5. Authentication must be explicitly configured for a deployable runtime. No hard-coded tenant or actor identity and no insecure permissive fallback.
6. The Engine is disposed during application shutdown.
7. The runtime must advertise only routes whose command boundaries are actually composed. Optional boundaries must not be replaced with placeholder objects.
8. The API factory remains usable for isolated tests with explicitly injected boundaries.

## Implementation and verification

- [x] Add an explicit runtime composition root for the create-case command and work queue.
- [x] Require database URL; default to database-backed RBAC authorization and configured OIDC/JWT PrincipalProvider unless explicit replacements are injected.
- [x] Scope create-case persistence adapters to one Session per execution.
- [x] Compose triage-case with the same UnitOfWork + idempotency/audit/outbox Session boundary; PostgreSQL HTTP tests verify persisted state, idempotent replay, request correlation, and cross-tenant denial.
- [x] Scope the work-queue reader to one Session per query and verify cleanup on query failure.
- [x] PostgreSQL HTTP integration: create a case, then query it in the same tenant's work queue.
- [x] PostgreSQL HTTP integration: verify a second tenant cannot see the first tenant's case.
- [x] Supported-Python CI passed on Python 3.12 and 3.13 for commit `3e8a1ced033c8f0e97f2a130bd4b6cce169b116f` (Runs #844 and #845).
- [x] Unit test: overlapping command executions use distinct Sessions and both contexts close — CI Runs #854/#855 passed on Python 3.12 and 3.13.
- [x] PostgreSQL integration: injected Outbox write failure returns an error and the created case is absent after rollback — CI Runs #862/#863 passed on Python 3.12 and 3.13.
- [x] PostgreSQL-backed overlapping HTTP create requests: both requests return 201 and both cases persist when the Outbox write path is deliberately overlapped — CI Runs #870/#871 passed on Python 3.12 and 3.13 for commit `191d3fcae473eecb710f786053e142eb605e7dc0`.
- [x] Add a provider-agnostic OIDC/JWT bearer adapter with explicit security configuration.
- [x] Add a persisted identity mapping model, migration, and exact-match active-mapping resolver (CI Runs #938/#939 passed on Python 3.12/3.13).
- [x] Wire configured OIDC settings and the database resolver into runtime composition when no provider is injected.
- [ ] Configure deployment-specific issuer/audience/JWKS/tenant claim and establish trusted identity/membership/role provisioning.
- [x] Verify RBAC migration and PostgreSQL authorization integration tests in CI on Python 3.12/3.13 — Runs #959/#960 passed at commit `2ff6fc635ba6779e4d097fc49e82e3ab3ff7958e` (182 tests each; Alembic check passed).
- [x] Require AuthorizationPort for read API composition and check per-route history/memory/work-queue permissions; CI Runs #967/#968 passed on Python 3.12/3.13 (184 tests each).
- [x] Implement and verify four-eyes approval attribution and enforcement; CI Runs #995/#996 passed on Python 3.12/3.13 (200 tests each).
- [x] Persist allow/deny authorization decisions in a dedicated audit table; fail closed if the policy check or audit write fails. CI Runs #1011/#1012 passed on Python 3.12/3.13 at commit `da4c67045073191df7307c88a2ea5f232b16cecc`.
- [x] Propagate request correlation IDs through command dataclasses into authorization decision audit; CI Runs #1023/#1024 passed on Python 3.12/3.13 with 204 tests each.
- [x] Approve audit retention/access policy defaults (365-day searchable window, security/operations-only access, no public query API, cleanup disabled pending legal-hold/archive design); deployment controls and restore evidence remain open in `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`.
- [ ] Cover any role/membership change path outside the trusted provisioning CLI.
- [x] Compose and test the triage-case route with explicit authorization, idempotency, outbox, tenant-scoped lookup, creator-attribution-preserving replay, and Session lifecycle; CI #1035 passed on Python 3.12/3.13 at commit `b65cfcb89dcd86cf510fe513a8880c2d933fa950` (206 tests per version, migration lifecycle and Alembic checks passed).
- [x] Compose and verify start-analysis route: `TRIAGED → ANALYZING`, idempotent replay, creator-attribution round-trip, and request correlation; CI #1039 passed on Python 3.12/3.13 at commit `0b65866ede42b6f34dec28b9308b47d1b89ce9a4` (207 tests per version, migration lifecycle and Alembic checks passed).
- [x] Verify create-evidence runtime composition and PostgreSQL end-to-end case progression (create → triage → start-analysis → evidence), persistence, and request correlation; CI Runs #1043/#1044 passed on Python 3.12/3.13 at commit `45ad57d8f5b598af32b49aa224cc70c51d0456f9` (208 tests per version, migration lifecycle and Alembic checks passed).
- [x] Verify add-analysis-finding runtime composition: PostgreSQL integration covers evidence linkage, finding persistence, idempotent replay, and correlation propagation; CI Runs #1047/#1048 passed on Python 3.12/3.13 at commit `b43943673671a8affcd360feeb4d2a58f9733c9e` (208 tests per version, migration lifecycle and Alembic checks passed).
- [x] Verify submit-options runtime composition: PostgreSQL integration covers evidence-backed finding prerequisite, option persistence, `ANALYZING → OPTIONS_READY` state/version transition, idempotent replay, and correlation propagation; CI Runs #1051/#1052 passed on Python 3.12/3.13 at commit `be9731824a6d24141b52ee132110ff2c33772188` (208 tests per version, migration lifecycle and Alembic checks passed).
- [x] Verify await-decision runtime: PostgreSQL integration covers `OPTIONS_READY → AWAITING_DECISION` (version 3 → 4), `AWAIT_DECISION` permission, idempotent replay, correlation propagation, and persisted state/version; CI Runs #1055/#1056 passed on Python 3.12/3.13 at commit `3c23c3a63772caa12490af8b748c24a2d0d1d7f1` (209 tests per version, migration lifecycle and `alembic check` passed).
- [ ] Compose further command routes only after their dependencies and lifecycles are explicit.
- [x] Compose create-action after approval with request-scoped persistence, `CREATE_ACTION` authorization, idempotency, audit/outbox, and correlation. PostgreSQL verifies `READY` state/version 1, decision/case linkage, persisted action, and stable replay. CI Runs #1071/#1072 passed on Python 3.12/3.13 at commit `e813cfe4ee07daee6d8bc6c6482d96e107f91cff`; migration lifecycle and `alembic check` passed.
- [ ] Compose start-action with READY/APPROVED preconditions, execution attempt persistence, replay, and case/action version checks.
- [x] Compose reject-decision with request-scoped persistence, `REJECT_DECISION` authorization, idempotency, audit/outbox, and correlation. PostgreSQL verifies `AWAITING_APPROVAL → REJECTED`, persisted decision/case state, and stable replay. CI Runs #1067/#1068 passed on Python 3.12/3.13 at commit `2d28eae82f42446211f90596e081953895090597`; migration lifecycle and `alembic check` passed.
- [ ] Compose further command routes only after their dependencies and lifecycles are explicit.
- [x] Compose approve-decision with request-scoped persistence, RBAC, four-eyes creator/decision-maker separation, idempotent replay, correlation, and persisted approval attribution. PostgreSQL verifies a distinct approver changes the decision and case to `APPROVED`, stores `approved_by`/`approved_at`, and replay is stable. CI Runs #1063/#1064 passed on Python 3.12/3.13 at commit `3117270462de0f52c3d12b13a6e9a6ee1125d249`; migration lifecycle and `alembic check` passed.
- [ ] Compose further command routes only after their dependencies and lifecycles are explicit.
- [x] Compose make-decision with request-scoped persistence, RBAC `MAKE_DECISION`, option loading, explicit `PolicyEvaluatorPort`, idempotency, audit/outbox, and correlation. PostgreSQL verifies decision persistence, approval-required state, case transition to `AWAITING_APPROVAL`, and idempotent replay. CI Runs #1059/#1060 passed on Python 3.12/3.13 at commit `c92fa0d3eb736d40aeecabce0d4dddb0267e6c49`; Alembic lifecycle and `alembic check` passed.
- [x] Make-decision route remains unmounted unless an explicit `PolicyEvaluatorPort` is injected; no default approval policy is inferred from RBAC.

## Acceptance criteria

- No module-global SQLAlchemy Session.
- Two overlapping requests never share a Session or transaction.
- Session cleanup occurs on both successful and exceptional paths.
- The same request's command adapters share one Session.
- Tenant identity comes only from the authenticated PrincipalProvider.
- PostgreSQL HTTP create/query and cross-tenant isolation tests pass.
- CI passes on supported Python versions.

## Status

**CREATE-CASE THROUGH CREATE-ACTION VERIFIED; START-ACTION SLICE IMPLEMENTED AND AWAITS CI. GATE STILL OPEN.** The create-case + work-queue composition, same-tenant/cross-tenant HTTP checks, overlapping PostgreSQL-backed HTTP create requests (both return 201 and persist), and rollback after an injected Outbox failure are verified in CI on Python 3.12 and 3.13. Concurrent command Session isolation is also unit-tested. Production identity-provider configuration, trusted-environment provisioning operations, operational evidence for audit retention, backup/restore, privileged access review (see `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`), and composition of additional command routes remain open. Create-case and triage-case runtime slices are CI-verified on Python 3.12/3.13 (CI #1035, 206 tests each). Start-analysis is composed with its own request-scoped UnitOfWork/idempotency/audit/outbox boundary and is CI-verified in #1039 (207 tests per Python version). Create-evidence is composed with the same transaction/reliability contract and verified in CI #1043/#1044 (208 tests per Python version). Add-analysis-finding is composed after evidence creation and verified in CI #1047/#1048 (208 tests per Python version). Submit-options is composed and its end-to-end PostgreSQL test advances `ANALYZING → OPTIONS_READY`; CI #1051/#1052 passed with 208 tests per Python version. Await-decision is now composed; its end-to-end PostgreSQL test advances `OPTIONS_READY → AWAITING_DECISION`, verifies replay, correlation, and persisted version 4; CI #1055/#1056 passed with 209 tests per Python version. Make-decision is composed only when an explicit PolicyEvaluatorPort is supplied; PostgreSQL verifies the selected option, persisted decision, approval-required status, `AWAITING_APPROVAL` case state, and idempotent replay; CI #1059/#1060 passed on Python 3.12/3.13 with migration checks passing. Approve-decision is composed and verified with a distinct approver, four-eyes checks, durable approval attribution, and idempotent replay; CI #1063/#1064 passed on Python 3.12/3.13 with migration checks passing. Reject-decision is now composed; PostgreSQL verifies rejection state, correlation, and replay, with CI #1067/#1068 passed on Python 3.12/3.13 and migration checks passing. Create-action is composed only after the case and decision are approved; PostgreSQL verifies READY state, persistence, linkage, correlation, and replay; CI #1071/#1072 passed on Python 3.12/3.13 with migration checks passing. Product-level retention/access defaults are approved, but this is not operational verification. Durable allow/deny authorization audit and fail-closed audit-write behavior passed CI Runs #1011/#1012. Command-path correlation propagation passed CI Runs #1023/#1024 with 204 tests per supported Python version. Four-eyes approval is implemented and verified by CI Runs #995/#996. Initial RBAC and permission-gated read APIs passed CI Runs #959/#960 and #967/#968 on Python 3.12/3.13. Resolver/runtime-auth tests and migration checks passed CI Runs #938/#939 on Python 3.12/3.13. This is not a deployment-readiness claim.
