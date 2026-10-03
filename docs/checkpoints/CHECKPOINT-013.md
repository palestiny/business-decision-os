# CHECKPOINT-013

## Scope

Authority consistency, fail-closed policy evaluation, and the reliability-boundary design gate.

## Verified

- CI run 92 for commit `02a4d2c1736e91af82d5341ed4a6c7466894a360` completed successfully.
- Create-case and triage command boundaries now require actor identity and authorization.
- Policy evaluation is authoritative for approval requirement.
- Policy evaluation failure is represented explicitly and is not treated as `approval_required=false`.
- Application coverage verifies that policy failure does not mutate the case, create a decision, or commit.
- PostgreSQL integration coverage verifies authority snapshot round-trip including policy identifiers.

## Architecture

Reliability is established as an application command boundary:

`Idempotency -> Authorization/Policy -> Domain Mutation -> Audit -> Outbox -> Idempotency Completion -> Commit`

The Unit of Work remains the atomic transaction owner.

## Decision

ADR-010 defines:

- tenant-scoped idempotency;
- deterministic request-hash conflict handling;
- explicit in-progress handling;
- append-only audit;
- transactional outbox;
- atomic persistence of domain state + reliability records;
- post-commit external publication;
- no full event sourcing for v0.1.

The first implementation proof will use `CreateDecisionCase` before generalizing the boundary.

## Remaining verification

- CI for the latest authority/reliability design commits must be green before implementation is considered verified.
- PostgreSQL adapters for idempotency/audit/outbox are not yet wired.
- The reusable application command execution boundary is not yet implemented.
- API exposure remains blocked until the reliability proof passes.
