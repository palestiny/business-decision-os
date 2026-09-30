# ADR-014 — Business Outcome and Verification Boundary

## Status

Accepted

## Context

A successfully executed Action only proves that an operational action completed. It does not prove that the business objective was achieved.

Decision OS therefore needs a separate Outcome and Verification layer.

## Decision

### Outcome

An Outcome records the business result observed after execution.

Lifecycle: PENDING → OBSERVED → VERIFIED | FAILED | UNKNOWN

An Outcome is associated with a Decision Case and may reference the Action/Execution that produced the observation.

### Verification

Verification evaluates an observed Outcome against an explicit expected outcome.

Verification status: PENDING, PASSED, FAILED, INCONCLUSIVE.

Verification retains the expected metric/condition, observed value/result, evaluation timestamp, verification method, and evidence references.

### Truth boundaries

- ActionExecution answers: Did the operational attempt complete?
- Outcome answers: What business result was observed?
- Verification answers: Does the observed result satisfy the expected condition?
- Decision Memory consumes verified facts; it does not redefine them.

### Determinism

Verification rules should be deterministic where the expected condition can be represented as structured data.

AI may summarize evidence, explain variance, and identify candidate interpretations. AI must not silently redefine the expected condition or mark a result verified without an explicit verification policy.

### Uncertainty

Missing or ambiguous evidence produces UNKNOWN or INCONCLUSIVE, not an invented success or failure.

## Initial implementation boundary

The first slice will use a simple structured expected/observed representation and deterministic verification. No AI verifier and no external analytics provider are introduced yet.

## Not yet locked

- Full metric expression language
- Multi-metric outcomes
- Time-window semantics
- Human override policy
- Automatic outcome collection
