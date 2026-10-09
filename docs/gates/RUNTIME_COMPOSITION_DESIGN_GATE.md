# Runtime Composition Design Gate

## Purpose

Define the production composition boundary for the existing Decision Core API before adding a deployment entry point.

## Current state

- The API factory accepts already-constructed command boundaries and readers.
- Persistence adapters currently hold SQLAlchemy Session instances.
- A runtime composition root now builds an Engine and Session factory, composes the create-case command boundary, and provides a session-factory-backed work-queue reader.
- The create-case UnitOfWork, idempotency, audit, and outbox adapters share one use-case-scoped Session.
- The queue reader opens and closes a Session per query.
- The runtime requires an explicit database URL and defaults to a database-backed, fail-closed RBAC AuthorizationPort; an explicit alternative adapter may be injected. If a PrincipalProvider is not injected, it builds the configured OIDC/JWT provider and database-backed identity resolver. The runtime now composes create-case and triage-case with request/use-case-scoped Sessions.
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
- [ ] Compose further command routes only after their dependencies and lifecycles are explicit.

## Acceptance criteria

- No module-global SQLAlchemy Session.
- Two overlapping requests never share a Session or transaction.
- Session cleanup occurs on both successful and exceptional paths.
- The same request's command adapters share one Session.
- Tenant identity comes only from the authenticated PrincipalProvider.
- PostgreSQL HTTP create/query and cross-tenant isolation tests pass.
- CI passes on supported Python versions.

## Status

**CREATE-CASE + TRIAGE-CASE RUNTIME SLICES IMPLEMENTED AND CI-VERIFIED; GATE STILL OPEN.** The create-case + work-queue composition, same-tenant/cross-tenant HTTP checks, overlapping PostgreSQL-backed HTTP create requests (both return 201 and persist), and rollback after an injected Outbox failure are verified in CI on Python 3.12 and 3.13. Concurrent command Session isolation is also unit-tested. Production identity-provider configuration, trusted-environment provisioning operations, operational evidence for audit retention, backup/restore, privileged access review (see `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`), and composition of additional command routes remain open. Create-case and triage-case runtime slices are CI-verified on Python 3.12/3.13 (CI #1035, 206 tests each). Product-level retention/access defaults are approved, but this is not operational verification. Durable allow/deny authorization audit and fail-closed audit-write behavior passed CI Runs #1011/#1012. Command-path correlation propagation passed CI Runs #1023/#1024 with 204 tests per supported Python version. Four-eyes approval is implemented and verified by CI Runs #995/#996. Initial RBAC and permission-gated read APIs passed CI Runs #959/#960 and #967/#968 on Python 3.12/3.13. Resolver/runtime-auth tests and migration checks passed CI Runs #938/#939 on Python 3.12/3.13. This is not a deployment-readiness claim.
