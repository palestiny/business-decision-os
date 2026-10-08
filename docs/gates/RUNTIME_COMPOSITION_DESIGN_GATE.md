# Runtime Composition Design Gate

## Purpose

Define the production composition boundary for the existing Decision Core API before adding a deployment entry point.

## Current state

- The API factory accepts already-constructed command boundaries and readers.
- Persistence adapters currently hold SQLAlchemy Session instances.
- A runtime composition root now builds an Engine and Session factory, composes the create-case command boundary, and provides a session-factory-backed work-queue reader.
- The create-case UnitOfWork, idempotency, audit, and outbox adapters share one use-case-scoped Session.
- The queue reader opens and closes a Session per query.
- The runtime requires an explicit database URL, authorization adapter, and PrincipalProvider; it does not invent authentication or an allow-all policy.
- Authentication is delegated to an explicitly injected PrincipalProvider; the default provider rejects requests without an authenticated principal.

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
- [x] Require database URL, authorization adapter, and PrincipalProvider; fail fast when required dependencies are missing.
- [x] Scope command persistence adapters to one Session per execution.
- [x] Scope the work-queue reader to one Session per query and verify cleanup on query failure.
- [x] PostgreSQL HTTP integration: create a case, then query it in the same tenant's work queue.
- [x] PostgreSQL HTTP integration: verify a second tenant cannot see the first tenant's case.
- [x] Supported-Python CI passed on Python 3.12 and 3.13 for commit `3e8a1ced033c8f0e97f2a130bd4b6cce169b116f` (Runs #844 and #845).
- [ ] Verify overlapping command requests use distinct Sessions and transactions.
- [ ] Verify runtime command rollback and cleanup on exceptional paths using PostgreSQL integration tests.
- [ ] Decide and implement the deployment authentication adapter/configuration; injected test providers are not production authentication.
- [ ] Compose and test additional command routes only when their dependencies and lifecycles are explicit.

## Acceptance criteria

- No module-global SQLAlchemy Session.
- Two overlapping requests never share a Session or transaction.
- Session cleanup occurs on both successful and exceptional paths.
- The same request's command adapters share one Session.
- Tenant identity comes only from the authenticated PrincipalProvider.
- PostgreSQL HTTP create/query and cross-tenant isolation tests pass.
- CI passes on supported Python versions.

## Status

**FIRST RUNTIME SLICE IMPLEMENTED; GATE STILL OPEN.** The create-case + work-queue composition and same-tenant/cross-tenant HTTP integration checks pass in CI on Python 3.12 and 3.13. Session concurrency, runtime rollback behavior, production authentication configuration, and composition of additional command routes remain unverified or out of scope. This is not a deployment-readiness claim.
