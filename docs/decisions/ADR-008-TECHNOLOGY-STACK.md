# ADR-008: Technology Stack

## Status

Accepted for MVP implementation.

## Decision

Use:

- Python 3.12+
- FastAPI for HTTP/API
- SQLAlchemy 2.x for persistence
- Alembic for migrations
- PostgreSQL as the production relational database
- pytest for tests

The domain remains framework-independent.

## Why

This stack fits the already approved modular-monolith architecture and preserves clean boundaries:

API → Application → Domain ← Infrastructure

FastAPI provides dependency injection and integrates naturally with authentication, security, and request-scoped dependencies. SQLAlchemy keeps persistence explicit and avoids coupling domain objects to ORM models. Alembic provides reproducible schema migrations.

## Alternatives considered

### SQLModel

Pros:
- simpler model declaration
- strong FastAPI ecosystem fit

Trade-off:
- combines API/data validation and persistence concerns more tightly than we want for a domain-heavy Decision OS.

### Django

Pros:
- mature batteries-included platform
- strong admin and ORM

Trade-off:
- larger framework surface and stronger framework coupling than required for the modular domain architecture.

### .NET / ASP.NET Core

Pros:
- excellent enterprise ecosystem
- strong typing and mature dependency injection

Trade-off:
- switching would add unnecessary implementation divergence from the project's Python-based experimentation and existing engineering context.

## Locked boundary

The choice of Python/FastAPI does NOT permit FastAPI, SQLAlchemy, PostgreSQL, or provider SDK imports inside the domain layer.
