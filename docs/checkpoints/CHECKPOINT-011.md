# CHECKPOINT-011

## Scope

Decision lifecycle completion through the approval boundary.

## Added

- Decision option invariants now reject duplicate selections.
- Available options are validated as belonging to the decision case before a decision is created.
- DecisionCase now has explicit transitions for:
  - recording a decision,
  - approval,
  - rejection.
- Making a decision now synchronizes the DecisionCase lifecycle:
  - approval required -> AWAITING_APPROVAL
  - no approval required -> APPROVED
- Approval now loads the decision through the tenant-scoped repository, persists the decision status, and advances the case.
- Rejection is an explicit application command and persists both decision and case state.
- Application tests cover the approval boundary, automatic approval path, approval, rejection, and decision-option integrity.

## Architectural boundary

Decision approval remains distinct from decision creation. A decision can exist in AWAITING_APPROVAL and cannot reach APPROVED without the explicit approval command.

## Verification boundary

GitHub Actions CI is triggered for the feature branch and is currently **PENDING** for the latest commit. No local runtime result is being claimed from this environment.

## Next

After CI is green:

1. verify PostgreSQL persistence for the full decision lifecycle, including approval/rejection state changes;
2. wire authority/policy ports into approval;
3. add API command boundaries only after the application lifecycle is proven.
