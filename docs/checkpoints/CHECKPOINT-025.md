# CHECKPOINT-025

## Scope

Resolve the Decision-stage lifecycle ambiguity and preserve optimistic concurrency.

## Decision lifecycle

The case lifecycle now explicitly preserves:

`AWAITING_DECISION → DECISION_MADE → AWAITING_APPROVAL`

or, when policy requires no approval:

`AWAITING_DECISION → DECISION_MADE → APPROVED`

This makes `DECISION_MADE` a real domain state rather than a declared-but-unreachable enum value.

The Decision entity's own status remains separate:
- `MADE`
- `AWAITING_APPROVAL`
- `APPROVED`
- `REJECTED`

Therefore:
- Case lifecycle answers where the DecisionCase is in the operational lifecycle.
- Decision status answers the authority state of the Decision itself.
- `DecisionMade != DecisionApproved` remains explicit.

## Concurrency

Because one command can perform the compound lifecycle transition from `AWAITING_DECISION` through `DECISION_MADE` to its authority-dependent terminal state, the persistence port now supports an explicit `expected_version`.

Make Decision captures the version read from persistence and saves against that exact version. This preserves optimistic concurrency rather than deriving the expected version from the final mutated version.

## Verification

The first CI run exposed a real concurrency invariant failure. It was fixed at the persistence boundary rather than weakening the concurrency check.

The next CI runs:
- #370 — PASS
- #371 — PASS

Python 3.12/3.13 are green.

## Result

Decision stage lifecycle semantics are now internally consistent and concurrency-safe.

## Next

Continue with the approval/rejection stage review, then move toward Action/Execution semantics. Do not implement Action until the distinction between an approved decision, an action intent, and an action execution is explicitly designed.
