# OPERATIONAL HARDENING DESIGN GATE

## Status

**PROPOSED — scope locked for implementation after review.**

## Objective

Strengthen the first vertical slice without adding new business capabilities, external integrations, or speculative infrastructure.

## Scope

Operational hardening must make existing guarantees easier to observe, verify, and protect.

### In scope

- Correlation/trace identifiers are preserved across command execution and HTTP boundaries.
- Reliability failures remain distinguishable from domain validation failures.
- Audit records retain actor, tenant, command, correlation, and outcome context.
- Outbox records retain enough metadata for safe publication and replay diagnosis.
- Tenant-scoped repository access is covered by cross-tenant negative tests.
- Idempotency replay behavior is covered at HTTP and persistence boundaries.
- Optimistic concurrency failures are observable as explicit contract errors.
- Architecture tests remain enforced in CI.
- CI evidence for the complete first slice is recorded.

### Out of scope

- Metrics/observability vendor integration.
- Distributed tracing infrastructure.
- New domain events.
- External action providers.
- AI/agent orchestration.
- Microservices.
- New business capabilities.
- General-purpose event sourcing.

## Acceptance Criteria

1. A successful command has auditable tenant, actor, command, correlation, and outcome context.
2. A failed command does not emit a success outbox event.
3. Same-key idempotent replay returns the original semantic result without duplicate business side effects.
4. Cross-tenant reads/writes cannot access another tenant's decision data.
5. Stale-version writes fail deterministically and do not partially persist.
6. HTTP error responses preserve the distinction between domain, authorization, idempotency, and concurrency failures.
7. Architecture guardrails pass in CI.
8. The first vertical slice remains green on supported Python versions and PostgreSQL.
