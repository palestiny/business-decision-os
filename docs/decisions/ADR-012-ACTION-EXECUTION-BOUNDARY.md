# ADR-012 — Action Intent and Execution Boundary

## Status
Accepted

## Context

A DecisionCase reaches APPROVED, but approval does not mean an external action has already happened.

The system must distinguish:
- the approved business intent
- the request to execute that intent
- each concrete execution attempt
- the external execution outcome

## Decision

Introduce two first-class concepts:

### Action
Represents the business action authorized by the Decision.

An Action is an intent/plan, not proof that anything was executed.

### ActionExecution
Represents one concrete attempt to execute an Action through an execution adapter.

One Action may have multiple executions because retries, provider failover, or reconciliation may be required.

## Lifecycle

Case:

`APPROVED → EXECUTING → OUTCOME_PENDING`

Action:

`PLANNED → READY → EXECUTING → COMPLETED | FAILED | BLOCKED`

Execution:

`REQUESTED → RUNNING → SUCCEEDED | FAILED | UNKNOWN`

`UNKNOWN` is not equivalent to failure. An UNKNOWN execution requires reconciliation before another execution is permitted.

## Reliability rules

1. The approval boundary must complete before an Action can become READY.
2. Creating an Action does not execute it.
3. Starting an Action creates an ActionExecution.
4. External timeout or ambiguous delivery produces UNKNOWN, not FAILED.
5. UNKNOWN executions block blind retry until reconciled.
6. Idempotency belongs to the execution boundary as well as the command boundary.
7. Audit and outbox records are written in the same transaction as internal state changes.
8. The execution adapter is behind a port; the domain never imports provider SDKs.
9. Protected actions may require a fresh authorization/policy check at execution time. Approval is evidence of authority at decision time, not permission to bypass current execution policy.
10. An ActionExecution completion is not an Outcome. Outcome verification remains a separate stage.

## Initial vertical slice

Implement only the internal lifecycle first:

`ApproveDecision → CreateAction → StartAction → ActionExecution`

No real external provider integration is introduced in this slice.

## Rejected alternatives

### Boolean execution flag
Rejected because it cannot represent attempts, UNKNOWN, retries, or reconciliation.

### Action as Decision fields
Rejected because a Decision expresses choice and rationale while Action expresses operational intent.

### Direct provider call from application handler
Rejected because it couples domain/application logic to external infrastructure and makes unknown outcomes unsafe.

## Open validation

The exact Action payload is case-type specific and must not be generalized prematurely. The initial model therefore keeps the business action type and opaque execution parameters at the application/integration boundary, while preserving the Action/Execution lifecycle as first-class domain state.
