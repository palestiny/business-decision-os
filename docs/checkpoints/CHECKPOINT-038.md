# CHECKPOINT-038 — Runtime Composition Design

## Status
**Runtime composition design documented; implementation not started.**

## Why this checkpoint exists
The Stage 10 API can accept a prebuilt Decision Work Queue reader, but the repository has no production composition root. Existing persistence components retain concrete SQLAlchemy Session instances, so constructing them once and sharing them across requests would create unsafe request/transaction lifecycle coupling.

## Design decisions
- Process-scoped Engine and Session factory; never a process-global Session.
- A request/use-case-scoped Session for each command execution.
- The UnitOfWork, repositories, idempotency, audit, and outbox adapters for one command share that command's Session/transaction.
- Read adapters must not retain a Session beyond their query request.
- Database URL is required; startup fails clearly when missing.
- Runtime authentication must be explicitly configured. Tenant and actor identities must never be hard-coded.
- Dispose the Engine during application shutdown.
- Only compose and expose routes with real implementations.

## Verification plan
1. RED tests for session uniqueness across requests and cleanup after success/failure.
2. Add a provider/composition seam so route handlers get request-scoped boundaries.
3. Compose create-case and work queue as the first runtime slice.
4. PostgreSQL HTTP integration: create a case, query it in the same tenant's queue, and prove cross-tenant isolation.
5. Run idempotency, audit, outbox, optimistic-concurrency, API contract, and tenant-isolation suites.
6. Close the gate only after supported-Python CI is green.

## Links
- Design gate: `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`
- Roadmap: `ROADMAP.md`
- Last verified queue slice: CI Run #806, https://github.com/palestiny/business-decision-os/actions/runs/37850119985

## Next step
Begin test-first implementation of request-scoped composition. No deployment-readiness claim is made by this checkpoint.
