# Application Architecture

## Dependency direction

API → Application → Domain ← Infrastructure

The Domain must not depend on FastAPI, SQLAlchemy, PostgreSQL, AI providers, or external ERP vendors.

## Commands

Commands express business intent:

- CreateDecisionCase
- TriageCase
- StartAnalysis
- CompleteAnalysis
- SubmitOptions
- MakeDecision
- ApproveDecision
- RejectDecision
- StartAction
- CompleteAction
- RecordOutcome
- VerifyOutcome
- CloseCase

Each command carries command_id, tenant_id, actor_id, correlation_id, causation_id, and where applicable an idempotency_key.

## Command handler flow

Authentication
→ tenant resolution
→ permission check
→ resource access
→ idempotency
→ load aggregate
→ domain validation
→ policy evaluation
→ persist state
→ append audit/event/outbox
→ commit

Handlers orchestrate. Domain objects enforce business invariants.

## Queries

Queries use dedicated read repositories/query services. They do not mutate state and do not require loading a full aggregate unless required by a specific read.

## Unit of Work

One internal business command is one transaction.

A successful transaction persists the business state change, audit record, domain event, and outbox message atomically.

## Transactional Outbox

Events that must leave the transaction are first persisted in an outbox record. A dispatcher publishes/processes them after commit.

This prevents the failure mode where business state commits but an event is lost.

## External actions

External side effects are not performed as an uncontrolled part of the database transaction.

Decision → Action → ActionExecution → Outbox → Worker → External system → Reconciliation → Outcome.

External execution requires idempotency and must distinguish FAILED from UNKNOWN.

## Authorization

Authentication, permission, policy, decision authority, and action authority are separate layers.

A permission to make a decision does not imply approval authority or permission to execute every resulting action.

## Concurrency

Aggregates use optimistic concurrency through a version field. A stale update results in an explicit concurrency conflict.

## Error contract

Errors expose stable machine-readable error codes and a correlation ID. Expected classes include validation, authentication, authorization, not-found, conflict, domain rejection, and dependency failure.

## Initial architecture decisions

- Modular monolith
- Relational PostgreSQL
- Explicit commands/queries
- Transactional outbox
- Append-only audit
- No full event sourcing
- No microservices initially
- AI behind ports/adapters
- ERP integrations behind ports/adapters
