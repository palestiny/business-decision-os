# CHECKPOINT-007

## Scope

Decision lifecycle application commands.

## Completed

- TriageCase command/handler.
- MakeDecision command/handler.
- ApproveDecision command/handler.
- Tenant-scoped DecisionCase loading.
- Application tests for command orchestration.
- Preserved the boundary between making and approving a decision.

## Deliberate limitation

The approval handler currently receives a Decision instance directly. This is a temporary application-layer test seam, not the final persistence design. The next persistence step will load decisions through a dedicated repository port and enforce authorization/policy before approval.

## Next

- Decision repository port.
- Policy evaluator and decision authority ports.
- Idempotency contract.
- Audit/outbox transaction contract.
