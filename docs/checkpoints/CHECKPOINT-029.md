# CHECKPOINT-029

## Scope

First Vertical Slice foundation: Evidence and Analysis for `PROJECT_MARGIN_RISK`.

## Status

PASS — implementation and CI verification completed.

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

GitHub Actions CI run #607 completed successfully on the branch head.

CI covered:

- Python 3.12
- Python 3.13
- PostgreSQL 17
- Alembic upgrade/downgrade/upgrade
- Alembic head check
- Alembic schema drift check
- pytest

The first vertical slice PostgreSQL integration test proves the closed loop reaches `CLOSED` with deterministic outcome verification.

## Next

- Verify CI and fix only demonstrated failures.
- If green, mark CHECKPOINT-029 PASS.
- Then complete the remaining first-slice hardening and record the next design/validation checkpoint.
