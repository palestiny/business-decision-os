# CHECKPOINT-006

## Scope

Decision and approval domain invariants.

## Completed

- Added Decision and DecisionOption domain objects.
- A decision must select at least one valid option.
- Selected options must belong to the same DecisionCase.
- Rationale is mandatory.
- Approval-required decisions remain AWAITING_APPROVAL after being made.
- Approval transitions a pending decision to APPROVED.
- Decisions without required approval can become APPROVED immediately.
- Approval is not represented as a boolean shortcut.

## Verification status

Tests have been committed as the executable contract. Runtime execution is pending because this environment cannot reach GitHub to clone the repository for local execution.

## Next

Implement application handlers and persistence ports, then verify them in CI/local development.
