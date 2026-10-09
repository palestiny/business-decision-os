# ADR-011 — HTTP API Contract

## Status

Accepted for the first HTTP proof.

## Scope

The first externally exposed command is POST /api/v1/decision-cases.

The API is an adapter over the proven application reliability boundary. It does not become a second application or transaction layer.

## Contract

### Identity

- actor_id and tenant_id come from an authenticated principal.
- They are never accepted from the request body.
- Authentication is supplied through an explicit principal-provider boundary.
- The initial repository does not invent a concrete authentication provider.

### Headers

- Idempotency-Key is required for the create command.
- X-Correlation-ID is optional.
- If omitted, the API generates a UUID.
- If supplied, it must be a UUID.
- The correlation identifier is propagated to the application reliability boundary and returned in the response and response header.

### Request

case_type, title, and optional case_id.

### Success

HTTP 201 with data and correlation_id.

The response is a stable DTO; domain objects are not exposed directly.

### Errors

- validation: 422
- authentication required: 401
- authorization denied: 403
- idempotency conflict: 409
- request in progress: 409
- domain conflict: 409
- policy unavailable: 503
- unexpected failure: 500

Error bodies use error.code, error.message, and correlation_id. Internal exception details are not exposed.

## Idempotency

The HTTP layer forwards the idempotency key unchanged to the reliability boundary.

The reliability boundary remains the authority for request hashing, duplicate detection, replay, transaction ownership, rollback, audit, and outbox durability.

The HTTP layer does not implement duplicate detection itself.

## Architectural Guardrails

HTTP → API mapping → Application Command → Reliability Boundary → Domain → Persistence

The API:
- does not access repositories;
- does not commit or rollback;
- does not mutate domain state directly;
- does not implement authorization policy;
- does not treat a client-supplied tenant as trusted identity;
- does not expose internal exception text.

## Deferred

Concrete authentication middleware/provider wiring is intentionally deferred until the authority/integration composition boundary is designed. The API contract already prevents callers from supplying actor or tenant identity directly.
