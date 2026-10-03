# ADR-013 — Execution Outcome and UNKNOWN Reconciliation

## Status

Accepted

## Context

Starting an Action creates an execution attempt, but that request is not proof of the external result. A provider can explicitly report success/failure, or the system can lose the outcome because of timeout/network ambiguity.

The system must prevent an ambiguous attempt from being retried blindly while still providing a deterministic path to recovery.

## Decision

Separate execution outcome handling from Action start.

### Execution transitions

- REQUESTED → RUNNING
- RUNNING → SUCCEEDED | FAILED | UNKNOWN
- UNKNOWN → SUCCEEDED | FAILED only through an explicit reconciliation operation.
- Terminal execution states cannot transition again.

### Action transitions

- Successful execution: EXECUTING → COMPLETED
- Failed execution: EXECUTING → FAILED
- UNKNOWN does not mark the Action failed or completed; the Action remains EXECUTING until reconciliation.

### Case transitions

- EXECUTING → OUTCOME_PENDING when an execution reaches a terminal known result.
- UNKNOWN leaves the Case in EXECUTING because execution truth is unresolved.

This keeps OUTCOME_PENDING available for the separate business Outcome stage rather than treating execution completion as business success.

## Reconciliation

ReconcileUnknownExecution is a first-class command.

It requires an execution currently in UNKNOWN, explicit authorization, and an observed provider outcome supplied by a trusted execution/integration boundary. It never performs a blind retry.

Reconciliation changes only the execution/action lifecycle. It does not create a business Outcome.

## Reliability

Completion and reconciliation are idempotent commands with audit and transactional outbox behavior.

The execution result is persisted before any external publication. No provider SDK is imported into the domain.

## Initial implementation boundary

Implement the internal state machine and application commands without a real provider.

A future provider adapter may report RUNNING, SUCCEEDED, FAILED, or UNKNOWN. Provider-specific payloads remain outside the domain model.
