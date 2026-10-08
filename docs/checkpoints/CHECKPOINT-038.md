# CHECKPOINT-038 — Runtime Composition First Slice

## Status
**First runtime slice implemented and verified in CI; runtime composition gate remains open.**

## Delivered
- Added a runtime composition root that requires an explicit database URL, authorization adapter, and authenticated PrincipalProvider.
- Engine and Session factory are process-scoped; each create-case execution uses a short-lived Session.
- The UnitOfWork, handler, idempotency, audit, and outbox adapters for create-case are composed over the same Session.
- The work-queue reader creates and closes a Session per query, including exceptional query exit.
- PostgreSQL HTTP integration creates a Decision Case and verifies it appears once in the same tenant's work queue.
- A second tenant's queue is verified not to expose that case.
- CI Runs #844 and #845 passed on Python 3.12 and 3.13 for commit `3e8a1ced033c8f0e97f2a130bd4b6cce169b116f`.
- Concurrent command executions are unit-tested to use distinct Sessions and close both contexts; CI Runs #854 and #855 passed on Python 3.12 and 3.13 for commit `f753c655f437c2e24e9de48fbf079ba1de7b7874`.

## Verification evidence
- CI #844: https://github.com/palestiny/business-decision-os/actions/runs/37853330867
- CI #845: https://github.com/palestiny/business-decision-os/actions/runs/37853337025
- Runtime composition gate: `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`

## Remaining before gate closure
1. Add PostgreSQL-backed tests for overlapping HTTP requests and transaction isolation; the current concurrency test is unit-level.
2. Verify command rollback and cleanup behavior on exceptional paths.
3. Configure a real deployment authentication provider; tests currently inject a controlled principal and authorization adapter.
4. Compose further command routes only after their authorization, transaction, and lifecycle dependencies are explicitly wired.
5. Run the full CI matrix again after these changes.

## Decision
Do not label this production-ready and do not mark the runtime gate PASS yet. The first slice is verified, but concurrent request isolation and deployable authentication are not yet established.
