# CHECKPOINT-009

## Scope

Persistence foundation for the first Decision OS vertical slice.

## Completed

- Added SQLAlchemy 2.x infrastructure base using modern DeclarativeBase/mapped_column mapping.
- Added PostgreSQL persistence models for tenants, DecisionCase, DecisionOption, Decision, selected options, idempotency, audit and outbox.
- Added Alembic environment and reproducible migrations 0001-0003.
- Added PostgreSQL UUID, timezone-aware timestamps and JSONB only at justified integration/reliability boundaries.
- Added database uniqueness for one decision per case and tenant-scoped idempotency keys.
- Kept persistence models under infrastructure; domain models remain framework-independent.
- Added FastAPI, SQLAlchemy, Alembic and psycopg dependencies according to the accepted technology ADR.

## Verification status

- GitHub source updated successfully.
- Local runtime execution is still NOT VERIFIED in this environment; tests and migrations must be executed against Python/PostgreSQL before claiming runtime success.

## Locked persistence decisions

- PostgreSQL is the MVP relational store.
- UUID identifiers are used for domain entities.
- UTC/timezone-aware timestamps are persisted with timestamptz semantics.
- State/status values remain strings with application/domain validation rather than PostgreSQL ENUMs.
- Migration history is reproducible from an empty database.
- Reliability records are persisted separately from business aggregates.

## Next

Add repository implementations and SQLAlchemy Unit of Work, then integration-test transaction boundaries, optimistic concurrency and tenant isolation before wiring API endpoints.
