# CHECKPOINT-029

## Scope

First Vertical Slice foundation: Evidence and Analysis for `PROJECT_MARGIN_RISK`.

## Status

IN PROGRESS — implementation is present; final CI verification pending.

## Design Gate

`docs/gates/FIRST_VERTICAL_SLICE_DESIGN_GATE.md` is PASS.

## Implemented

- Immutable `Evidence` domain primitive.
- Explicit `AnalysisFinding` classification: FACT / INFERENCE / HYPOTHESIS.
- Evidence references required for analysis findings.
- Tenant-scoped evidence and analysis repository ports.
- PostgreSQL persistence models.
- Alembic migration `0006_evidence_analysis`.
- CreateEvidence command + reliability boundary.
- AddAnalysisFinding command + reliability boundary.
- HTTP endpoints for evidence and analysis findings.
- UnitOfWork wiring.
- Decision options now require at least one persisted analysis finding.
- PostgreSQL integration coverage for evidence/analysis replay and single side effects.
- PROJECT_MARGIN_RISK end-to-end integration test covering the closed loop through verification and closure.

## Architectural Notes

- Evidence is immutable.
- Analysis does not redefine evidence.
- Fact, inference, and hypothesis remain explicit.
- AI is not required for the slice.
- Existing reliability, audit, outbox, tenant, and transaction boundaries are reused.

## Verification

Pending CI on the latest branch head.

## Next

- Verify CI and fix only demonstrated failures.
- If green, mark CHECKPOINT-029 PASS.
- Then complete the remaining first-slice hardening and record the next design/validation checkpoint.
