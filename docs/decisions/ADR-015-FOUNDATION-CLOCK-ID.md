# ADR-015 — Clock and ID Abstractions

## Status

**Accepted — defer until a demonstrated domain requirement exists.**

## Context

The foundation currently leaves Clock and ID abstractions open. The first vertical slice does not require domain time as a business input, and command boundaries already allow callers to provide identifiers where identity is part of the command contract.

Introducing abstractions only for test substitution would add indirection without protecting a current domain invariant.

## Decision

Do **not** introduce Clock or ID ports in the current foundation.

### ID policy

- Domain entities receive their IDs explicitly.
- Application commands may accept an optional caller-supplied ID where idempotent identity is part of the command contract.
- Infrastructure may provide persistence defaults only as a defensive adapter concern.
- Application/domain code must not depend on persistence-generated identity.
- If a future workflow requires deterministic ID generation, replay-safe ID derivation, or an ID-generation policy as business behavior, introduce an explicit ID port at that boundary.

### Clock policy

- Domain logic must not call wall-clock APIs directly.
- Persistence timestamps remain infrastructure concerns unless time becomes part of a domain invariant.
- If expiry, scheduling, temporal eligibility, or time-window behavior becomes a domain rule, introduce an explicit Clock port before implementing that rule.

## Consequences

### Positive

- No speculative abstraction layer.
- Deterministic domain tests remain possible because time and identity are explicit inputs when they matter.
- The modular-monolith dependency direction remains simple.

### Trade-off

Future temporal or identity policies may require a later refactor from infrastructure/application helpers to explicit ports. That cost is accepted because no current domain rule requires those abstractions.

## Trigger Conditions

Revisit this ADR when any of the following is introduced:

1. Domain behavior depends on current time.
2. A domain rule depends on reproducible time during replay.
3. ID generation itself becomes a business policy.
4. Distributed uniqueness or deterministic replay requires an application-level ID generator.
5. Scheduling/expiry semantics become part of the Decision OS domain.
