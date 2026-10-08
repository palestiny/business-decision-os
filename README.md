# Business Decision OS

Business Decision Operating System (Decision OS).

## Purpose

Decision OS is not an ERP replacement. It is a decision-and-execution layer that connects business signals to evidence, analysis, decisions, controlled actions, outcomes, verification, and organizational learning.

## Core lifecycle

Signal → Case → Evidence → Analysis → Options → Decision → Approval → Action → Outcome → Verification → Learning

## Initial vertical slice

Project / Delivery Performance Decisions, starting with `PROJECT_MARGIN_RISK`.

## Architecture and implementation status

- Application Architecture Gate: PASS.
- Stages 0–9: foundation, Decision Core, reliability, vertical slices, Decision Memory, and read-only Decision History implemented and gated as recorded in `ROADMAP.md`.
- Stage 10: tenant-scoped read-only Decision Work Queue implemented; CI Run #806 passed.
- API query: `GET /api/v1/decision-work-queue`, enabled when `create_app` receives a `DecisionWorkQueueReader`.
- Runtime composition design: documented in `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`; implementation and verification remain pending.
- Runtime limitation: this repository currently provides an application factory and dependency-injection contracts, not a deployment composition root. A runtime entry point must wire request-scoped database sessions and explicit authentication before treating the API as a deployed service.

See `docs/gates/HUMAN_DECISION_WORKFLOW_DESIGN_GATE.md` for the queue slice scope and `ROADMAP.md` for current stage status.
