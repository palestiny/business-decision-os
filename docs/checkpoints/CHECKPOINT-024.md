# CHECKPOINT-024

## Scope

Close the pre-decision Options stage and transition to AWAITING_DECISION.

## Completed

### Options
- Added explicit `SUBMIT_OPTIONS` authorization.
- Added `SubmitOptionsCommand` and transaction-neutral handler.
- Added persistent option creation through the DecisionOption repository port.
- Added domain validation for option titles.
- Enforced:
  - at least one option
  - unique option IDs within the submission
  - no duplicate option submission for a case
  - options belong to the target case
- Added `SubmitOptionsReliabilityBoundary`.
- Added HTTP:
  - `POST /api/v1/decision-cases/{case_id}/options`
- Added deterministic request hashing, replay serialization, audit and transactional outbox.
- Added PostgreSQL replay proof.

### Await Decision
- Added explicit `AWAIT_DECISION` authorization.
- Added `AwaitDecisionCommand` and transaction-neutral handler.
- Handler requires persisted options before the case can enter `AWAITING_DECISION`.
- Added `AwaitDecisionReliabilityBoundary`.
- Added HTTP:
  - `POST /api/v1/decision-cases/{case_id}/decision/await`
- Added replay, audit, outbox and PostgreSQL persistence proof.

## Verified lifecycle

`TRIAGED → ANALYZING → OPTIONS_READY → AWAITING_DECISION`

## Verification

PASS — latest CI runs #354 and #355 succeeded; the branch also passed the preceding matrix runs. Python 3.12/3.13, Alembic lifecycle/checks and full pytest are green.

## Architectural decision

Options are persisted as first-class domain data. The system does not treat `OPTIONS_READY` as a boolean flag or embed options in an opaque JSON payload.

The transition to `AWAITING_DECISION` is an explicit command and requires at least one persisted option.

## Next

Proceed with the Decision stage review: make-decision semantics, authority evaluation, approval branching, and whether the current `DecisionCase` lifecycle should retain `DECISION_MADE` as a distinct state or continue directly into approval/approved semantics.
