# Domain Model

## Decision Case

DecisionCase is the central business aggregate.

Initial lifecycle:

DETECTED → TRIAGED → ANALYZING → OPTIONS_READY → AWAITING_DECISION → DECISION_MADE → AWAITING_APPROVAL / APPROVED → EXECUTING → OUTCOME_PENDING → VERIFYING → CLOSED

Exceptional states include REJECTED, CANCELLED, BLOCKED, FAILED, and EXPIRED.

## Core distinction

**DecisionMade != DecisionApproved**

A decision can exist while policy requires one or more approvals.

**ActionCompleted != BusinessSuccess**

An action records execution. Outcome and verification establish whether the business objective was achieved.

## Evidence

Evidence is a captured business fact/reference with:

- source
- metric
- value
- unit
- period
- captured_at
- confidence
- snapshot/reference

Evidence should be immutable. A changed source produces new evidence.

## Analysis

Analysis separates:

- Fact
- Inference
- Hypothesis
- Confidence

AI-generated analysis cannot silently convert inference into fact.

## Options

Each option records expected impact, cost, risk, assumptions, dependencies, confidence, and provenance.

## Decision

A decision records selected options, rationale, actor, time, authority snapshot, and provenance.

Human rationale is distinct from an AI recommendation.

## Approval

Approval is first-class and may be required by policy.

MVP supports ALL_REQUIRED approval semantics. More complex approval strategies are deferred until justified.

## Actions

Action represents business intent.

ActionExecution represents an individual execution attempt.

Execution states:

PENDING, RUNNING, SUCCEEDED, FAILED, UNKNOWN, CANCELLED.

UNKNOWN means the external result is not safely known and requires reconciliation before a potentially duplicating retry.

## Outcome

ExpectedOutcome defines the intended measurable result.

ActualOutcome records the measured result.

Verification determines SUCCESS, PARTIAL, FAILED, or INCONCLUSIVE.

## Closure

A case is normally closed only after required decision, actions, outcome, and verification are complete. Exceptional closure requires an explicit reason.

## Decision Memory

Decision Memory is a derived projection of verified business history. It is not the source of truth.

Principle:

> Memory can recommend; the domain decides truth.
