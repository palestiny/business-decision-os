# CHECKPOINT-016 — Generic Reliability Executor Adoption

## Status

**PASS**

## Verified

The application reliability mechanics are now centralized in `ReliabilityExecutor`.

Two materially different command boundaries use the executor:

- `CreateDecisionCaseReliabilityBoundary`
- `TriageCaseReliabilityBoundary`

Command-specific semantics remain explicit in `ReliabilitySpec`:

- tenant extraction
- request hashing
- actor extraction
- command execution
- entity identity/type
- response serialization/deserialization
- outbox topic and payload
- response status

The executor owns only the shared reliability mechanics:

1. idempotency reservation
2. completed-request replay
3. audit append
4. outbox append
5. idempotency completion
6. single transaction commit
7. rollback on failure

## Evidence

CI run #161 completed successfully.

- Python 3.12: PASS
- Python 3.13: PASS
- Alembic upgrade/downgrade lifecycle: PASS
- Alembic head/check validation: PASS
- pytest: PASS

The existing command-specific reliability tests continue to pass after migration to the generic executor.

## Architectural Guardrails

- Domain remains unaware of reliability infrastructure.
- Command handlers remain transaction-neutral.
- Unit of Work remains the sole transaction owner.
- Authorization/policy semantics remain in command handlers and authority ports.
- ReliabilitySpec does not become a hidden policy or authorization layer.
- PRs remain unmerged pending explicit owner approval.

## Decision

The generic executor is accepted as the application-level reliability primitive for subsequent retryable commands.

## Next Proof

Prove post-commit outbox publication semantics before exposing the HTTP API:

`transaction commit → durable outbox → publication attempt → acknowledgement/retry`

The proof must distinguish durable database state from external delivery state and must not treat an external timeout as confirmed failure.
