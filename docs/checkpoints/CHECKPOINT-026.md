# CHECKPOINT-026

## Scope

Establish the Action / ActionExecution boundary before external execution work.

## Decisions

- Action is business intent authorized by a Decision.
- ActionExecution is a concrete execution attempt.
- An Action may have multiple execution attempts.
- UNKNOWN is a first-class execution result and is not treated as FAILED.
- Action completion is not Outcome verification.
- No provider integration is introduced in this stage.

## Added

- `docs/decisions/ADR-012-ACTION-EXECUTION-BOUNDARY.md`
- `docs/gates/ACTION_DESIGN_GATE.md`
- `domain/action.py`
- Action and ActionExecution repository ports.

## Current lifecycle

Case:
`APPROVED → EXECUTING → OUTCOME_PENDING`

Action:
`PLANNED → READY → EXECUTING → COMPLETED | FAILED | BLOCKED`

Execution:
`REQUESTED → RUNNING → SUCCEEDED | FAILED | UNKNOWN`

## Verification status

NOT YET PROVEN.

The domain primitives and ports are added, but persistence, commands, reliability boundaries, API contracts, migrations, and PostgreSQL replay tests are still required.

## Next

Implement Action persistence and the first internal vertical slice:
`CreateAction → StartAction → ActionExecution`.

Do not connect an external provider until this slice is green.
