# CHECKPOINT-005

## Scope

DecisionCase domain foundation and initial TDD contract.

## Completed

- Created Python project skeleton.
- Added DecisionCase domain type.
- Added explicit lifecycle status values.
- Added initial lifecycle transition rules.
- Added optimistic version increment behavior.
- Added initial unit tests covering creation, valid transitions, invalid transitions, and closed-case immutability.

## Important status

The current tests define the intended contract. They must be executed in a real environment before the checkpoint is considered verified.

## Next

Extend the RED suite for:
- options
- decisions
- approval requirements
- decision authority
- closure invariants

Then implement the missing domain behavior and verify the complete suite.
