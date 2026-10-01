# OPERATIONAL HARDENING DESIGN GATE

## Status

**PASS — implementation and CI verification complete.**

## Objective

Strengthen the first vertical slice without adding new business capabilities, external integrations, or speculative infrastructure.

## Scope

Operational hardening makes existing guarantees easier to observe, verify, and protect.

### In scope

- Correlation/trace identifiers across command and HTTP boundaries.
- Distinguishable reliability failures and domain validation failures.
- Audit records retaining actor, tenant, command, correlation, and outcome context.
- Outbox records retaining tenant/correlation metadata for publication and replay diagnosis.
- Tenant-scoped repository access with cross-tenant negative coverage.
- Idempotency replay and conflict behavior at HTTP and persistence boundaries.
- Explicit optimistic concurrency contract errors.
- Architecture guardrails enforced in CI.
- CI evidence for the complete first slice.

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

| # | Criterion | Evidence |
|---|---|---|
| 1 | Successful command has tenant, actor, command, correlation, and outcome audit context | Reliability executor + audit persistence tests |
| 2 | Failed command does not emit a success outbox event | Atomic rollback tests for create/triage reliability paths |
| 3 | Same-key replay returns original semantic result without duplicate side effects | HTTP replay tests across create, triage, decision, approval/rejection, options, and await-decision flows |
| 4 | Cross-tenant reads/writes cannot access another tenant's decision data | Decision-case tenant isolation + tenant-scoped idempotency tests; write predicates include tenant |
| 5 | Stale-version writes fail deterministically without partial persistence | PostgreSQL optimistic-concurrency test with explicit ConcurrencyConflict |
| 6 | HTTP errors distinguish domain, authorization, idempotency, and concurrency failures | API error-mapping tests; stable error codes and correlation IDs |
| 7 | Architecture guardrails pass in CI | CI run #661 |
| 8 | First vertical slice remains green on supported Python versions and PostgreSQL | CI run #661: Python 3.12 and 3.13, PostgreSQL migrations and pytest green |

## Verification

- Commit: 354edd38d3662af9d2afca37925a32330c3a2b7a
- CI: **Run #661 — success**
- Migration cycle: upgrade → downgrade → upgrade → head check → alembic check passed.
- Reliability coverage includes success, rollback, replay, conflict, concurrency, tenant isolation, and HTTP error contracts.

## Decision

Operational hardening acceptance criteria are satisfied. No additional observability infrastructure or business capability is introduced by this gate.

## Next Gate

Proceed to the next business/domain capability only after recording the checkpoint for this gate closure.
