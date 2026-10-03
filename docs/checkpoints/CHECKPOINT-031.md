# CHECKPOINT-031

## Scope

Foundation decision for Clock/ID abstractions and the next operational-hardening gate.

## Status

DESIGN-LOCKED

## Decision

Clock and ID abstractions are intentionally deferred.

The current system does not have a domain invariant requiring current time or an ID-generation policy. Adding ports now would create indirection without protecting a demonstrated behavior.

The decision is recorded in:

`docs/decisions/ADR-015-FOUNDATION-CLOCK-ID.md`

## Next Gate

First-slice operational hardening is now explicitly scoped by:

`docs/gates/OPERATIONAL_HARDENING_DESIGN_GATE.md`

The next implementation work must verify existing guarantees rather than add new business capabilities.

## Constraints

- No speculative observability platform.
- No new domain layer.
- No external provider integration.
- No AI dependency.
- Preserve tenant, idempotency, concurrency, audit, outbox, and transaction boundaries.

## Verification

This checkpoint is documentation-only. CI verification is required after the operational-hardening implementation changes.

## Next

Implement the operational-hardening gate from tests first, then make only the smallest code changes required by demonstrated failures.
