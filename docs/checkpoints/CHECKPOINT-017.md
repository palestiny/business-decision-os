# CHECKPOINT-017 — Transactional Outbox Publication

## Status

**PASS**

## Verified

Post-commit outbox publication is now explicitly separated from the command transaction.

The verified flow is:

`command transaction → durable outbox row → post-commit publication attempt → mark published → publication transaction commit`

The publication boundary distinguishes:

- **published / outcome known** — external publisher returned successfully and the database publication marker was committed.
- **not published / outcome unknown** — external delivery acknowledgement timed out; the durable outbox row remains unpublished and eligible for reconciliation/retry.

## Evidence

CI run #189 completed successfully.

- Python 3.12: PASS
- Python 3.13: PASS
- Alembic upgrade/downgrade lifecycle: PASS
- Alembic head/check validation: PASS
- pytest: PASS

Integration proof covers PostgreSQL persistence for:

1. successful external publication persists `published_at`;
2. unknown external delivery outcome leaves `published_at` NULL.

Unit proof covers:

1. publication is marked only after external success;
2. unknown outcome is not marked published;
3. already-published records are not republished;
4. publication transaction commit/rollback is explicit.

## Architectural Guardrails

- Command handlers remain transaction-neutral.
- The command reliability boundary owns the command transaction.
- The outbox repository does not commit implicitly.
- The post-commit publication service owns the publication transaction boundary explicitly.
- External delivery state is not conflated with database durability.
- UNKNOWN delivery outcome is not converted into confirmed failure.
- Transactional outbox remains a durable fact mechanism, not event sourcing.
- PRs remain unmerged pending explicit owner approval.

## Decision

Post-commit outbox publication is accepted as the reliability mechanism for durable asynchronous delivery.

## Next Proof

Define and prove the HTTP/API contract over the already-proven application boundaries:

- request validation
- authentication/authorization error mapping
- idempotency-key semantics
- replay response semantics
- domain/application error mapping
- correlation identifier propagation
- stable response envelopes

The API must not introduce a second transaction mechanism.
