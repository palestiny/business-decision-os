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
- PostgreSQL integration injects an Outbox write failure and verifies the new case is absent after rollback; CI Runs #862 and #863 passed on Python 3.12 and 3.13 for commit `dcccaf2816479f20613993058231f99ee3fbc05a`.
- PostgreSQL-backed overlapping HTTP create requests force overlap inside the Outbox write path and verify both requests return 201 and both cases persist; CI Runs #870 and #871 passed on Python 3.12 and 3.13 for commit `191d3fcae473eecb710f786053e142eb605e7dc0`.

## Verification evidence
- CI #844: https://github.com/palestiny/business-decision-os/actions/runs/37853330867
- CI #845: https://github.com/palestiny/business-decision-os/actions/runs/37853337025
- CI #870: https://github.com/palestiny/business-decision-os/actions/runs/37856028446
- CI #871: https://github.com/palestiny/business-decision-os/actions/runs/37856033069
- Runtime composition gate: `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`

## Authentication adapter progress
- Added `OIDCJWTPrincipalProvider` using PyJWT/JWKS, fixed RS256 algorithm, explicit issuer/audience/JWKS/tenant claim configuration, bounded clock skew, and a resolver contract that maps external identities to internal UUIDs.
- Added unit coverage for valid mapping, missing/non-bearer credentials, invalid issuer/audience/expiry/claims, unknown mapping, and bad signatures. CI Runs #890 and #891 passed on Python 3.12 and 3.13 for commit `da5ead3c81e3cd170536d1dda1d6e9b4a915dfcc`: https://github.com/palestiny/business-decision-os/actions/runs/37857658649 and https://github.com/palestiny/business-decision-os/actions/runs/37857662934.
- The deployment's actual identity provider configuration and production resolver implementation remain open.

## Remaining before gate closure
1. Run CI on the current documentation HEAD and keep the OIDC adapter suite green on Python 3.12 and 3.13.
2. Configure the deployment issuer/audience/JWKS/tenant claim and implement a production-grade external identity resolver.
3. Wire the configured provider into the runtime entry point and test invalid-token rejection over HTTP.
4. Compose further command routes only after their authorization, transaction, and lifecycle dependencies are explicitly wired.
5. Add product-facing queue usability and operator workflow validation.

## Decision
Do not label this production-ready and do not mark the runtime gate PASS yet. The first slice, including overlapping PostgreSQL-backed HTTP creates and rollback verification, is CI-verified. Deployable authentication and further command-route composition are not yet established.
