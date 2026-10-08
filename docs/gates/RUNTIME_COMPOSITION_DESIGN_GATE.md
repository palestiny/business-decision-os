# Runtime Composition Design Gate

## Purpose

Define the production composition boundary for the existing Decision Core API before adding a deployment entry point.

## Current state

- The API factory accepts already-constructed command boundaries and readers.
- Persistence adapters currently hold SQLAlchemy Session instances.
- Integration tests manually assemble adapters around a test Session.
- No production composition root currently exists.
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

## Implementation sequence

1. Add failing tests for distinct Sessions across requests, closure after success/failure, and no cross-request transaction sharing.
2. Introduce a composition/provider seam so route handlers obtain a boundary built for the request Session rather than capturing one Session-backed boundary at app construction time.
3. Compose create-case and work-queue first as the smallest useful runtime slice.
4. Add PostgreSQL HTTP integration coverage: POST a case, then GET the work queue for the same tenant and confirm visibility; verify another tenant cannot see it.
5. Run existing idempotency, audit, outbox, optimistic concurrency, tenant-isolation, and API contract suites.
6. Only after CI passes, mark the gate PASS and expand runtime composition to other commands.

## Acceptance criteria

- No module-global SQLAlchemy Session.
- Two overlapping requests never share a Session or transaction.
- Session cleanup occurs on both successful and exceptional paths.
- The same request's command adapters share one Session.
- Tenant identity comes only from the authenticated PrincipalProvider.
- PostgreSQL HTTP create/query and cross-tenant isolation tests pass.
- CI passes on supported Python versions.

## Status

DESIGN DEFINED — implementation and verification pending. This is not a deployment-readiness claim.
