# CHECKPOINT-014

## Scope

PostgreSQL reliability-boundary proof for the first externally retryable command: `CreateDecisionCase`.

## Verified

- CI Run #145 (`36421955469`) completed successfully.
- Python 3.12 test job passed.
- Python 3.13 test job passed.
- Both jobs completed Alembic upgrade/downgrade/head checks successfully.
- PostgreSQL integration tests passed as part of the CI test suite.
- `CreateDecisionCaseReliabilityBoundary` was verified against real SQLAlchemy/PostgreSQL persistence.
- Successful execution persists the decision case, audit event, outbox message, and completed idempotency record.
- Forced failure during idempotency completion rolls back the decision case, audit event, outbox message, and idempotency record together.
- Idempotency conflict and replay semantics remain covered by application tests.

## Architecture

The proven transaction boundary is:

`reserve idempotency -> authorize -> domain mutation -> audit -> outbox -> complete idempotency -> single UoW commit`

Handlers remain transaction-neutral. The Unit of Work owns the database transaction.

## Decision

The reliability-boundary design gate for the first command is **PASS**.

The proof is intentionally limited to `CreateDecisionCase`; the boundary will not be generalized merely for abstraction's sake. Additional command types must first demonstrate the same transactional and semantic requirements.

## Remaining verification

- Prove a second representative command before extracting a generic reusable execution abstraction.
- Extend real PostgreSQL atomicity coverage to the chosen second command.
- Verify post-commit outbox publication semantics separately from database transaction success.
- Review API error/idempotency contract before API exposure.
- API exposure remains blocked until the broader reliability contract is verified.

## Guardrails

- Do not merge PR #2 without explicit owner approval.
- Do not introduce full event sourcing for v0.1.
- Do not move transaction ownership into domain entities or command handlers.
- Do not treat successful database commit as proof that external publication succeeded.
