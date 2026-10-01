# Design Gate

## Status

**PASS for implementation of the thin vertical slice.**

This gate does not mean commercial validation is complete.

## Locked decisions

- Product: Business Decision Operating System
- Positioning: decision/execution layer, not ERP replacement
- Initial wedge: project/delivery performance decisions
- Architecture: modular monolith
- Core abstraction: DecisionCase
- Lifecycle: Signal → Case → Evidence → Analysis → Options → Decision → Approval → Action → Outcome → Verification → Learning
- Human/policy authority is explicit
- Relational persistence
- PostgreSQL
- Append-only audit
- Transactional outbox
- Idempotency
- Optimistic concurrency
- Integration through ports/adapters
- AI outside the domain core

## Rejected for initial implementation

- Building a full ERP
- AI-first architecture
- Autonomous approval
- Microservices
- Full event sourcing
- Graph database
- Provider-specific domain coupling

## Open validation questions

- Exact paying buyer
- Willingness to pay
- Quantified ROI
- Initial vertical market
- Strength of Decision Memory as a moat

## Next gate

Application implementation + TDD RED.
