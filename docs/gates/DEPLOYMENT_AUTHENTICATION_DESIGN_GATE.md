# Deployment Authentication Design Gate

## Status
**OIDC/JWT ADAPTER, PERSISTED IDENTITY RESOLVER, AND RUNTIME AUTO-WIRING IMPLEMENTED — DEPLOYMENT CONFIGURATION REMAINS OPEN.** The provider validates configured RS256 bearer tokens and delegates verified identity mapping to a server-managed database mapping. It is not yet a complete deployment configuration.

## Security invariants
- Requests without valid authenticated identity fail closed.
- Actor identity is derived from a verified identity, never from a request body or arbitrary header.
- Tenant identity is selected through an exact server-managed mapping for the verified issuer, subject, and configured tenant claim. Client-supplied tenant IDs are never authoritative.
- Identity mappings are provisioned by trusted administrative/deployment processes; a token or request cannot create or alter mappings.
- Authentication and authorization remain separate: a valid identity does not automatically grant Decision Core permissions.
- Test PrincipalProviders are only for tests; they must not be used as production defaults.
- Invalid, expired, wrong-issuer, wrong-audience, malformed, or unverifiable credentials are rejected.
- Tokens, secrets, and sensitive claims are not written to application logs.

## Options

| Option | Strengths | Risks / constraints | Fit |
|---|---|---|---|
| OIDC/OAuth2 bearer access token, JWT validation using issuer metadata/JWKS | Standard identity provider integration; key rotation; fits browser/mobile and multi-tenant SaaS | Must configure issuer, audience, algorithms, claim mapping, clock skew, and key-cache behavior | **Recommended default for a deployable multi-tenant product** |
| Trusted reverse-proxy identity headers | Can fit a controlled internal deployment with an identity-aware proxy | Unsafe if the app is reachable directly or proxy headers are not stripped and overwritten; deployment-specific | Private deployment only, with network controls and explicit trust boundary |
| Static API keys | Simple for service-to-service integrations | Rotation/revocation and tenant/actor scoping must be built; poor fit for interactive users | Optional future machine-client adapter, not the primary user auth |
| Injected PrincipalProvider | Keeps application independent of identity provider and enables deterministic tests | Provides no authentication by itself | Composition seam only; provider implementation must be supplied |

## Recommended implementation contract
1. Implement a concrete OIDC/JWT PrincipalProvider behind the existing PrincipalProvider callable.
2. Require explicit configuration for issuer, audience, and trusted tenant/actor claim mapping; fail startup if required values are absent.
3. Validate signature against issuer-published keys, fixed allowed algorithms, issuer, audience, expiry, and not-before claims; use bounded clock skew and safe key refresh.
4. Resolve the external subject and tenant claim to internal UUIDs through an explicit mapping contract. Do not assume external IDs are UUIDs.
5. Keep AuthorizationPort separate and fail closed when policy evaluation is unavailable.
6. Add unit tests for missing/bad/expired/wrong-issuer/wrong-audience tokens, key rotation behavior, missing tenant mapping, and valid principal extraction.
7. Add API tests proving spoofed tenant headers/body fields cannot change tenant scope, plus tenant-isolation tests using distinct verified principals.
8. Document secret/configuration handling and deployment network boundaries.

## Decisions still required
- Identity provider and issuer URL.
- Expected audience/resource identifier.
- Which verified claim or server-side mapping identifies the tenant.
- Whether this first deployment is public SaaS or behind a private trusted proxy.
- Trusted provisioning workflow and administration controls for mapping rows.

## Identity mapping contract
- external_identity_mappings uniquely maps the tuple (issuer, subject, tenant_key) to internal actor_id and tenant_id.
- tenant_id references an existing tenant with restrictive delete behavior.
- Only is_active = true mappings resolve; inactive, unknown, and mismatched identities fail closed.
- Mapping writes are intentionally not exposed through public application routes. They must be provisioned through a trusted administrative/database migration process.
- actor_id references `actors.id`. Migration 0011 creates actor lifecycle rows for existing mappings but does not create memberships or role assignments. Authentication does not automatically authorize a command.

## Implementation status
- [x] Add an OIDC/JWT PrincipalProvider adapter with explicit issuer, audience, JWKS URL, and tenant-claim configuration.
- [x] Restrict token verification to RS256 and validate signature, issuer, audience, expiry, issued-at, and required subject/tenant claims.
- [x] Add a fail-fast environment factory for OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL, and OIDC_TENANT_CLAIM; optional OIDC_CLOCK_SKEW_SECONDS is bounded to 0–120 seconds.
- [x] Add external_identity_mappings model and Alembic migration with unique external identity key and tenant foreign key.
- [x] Add a Session-scoped SQLAlchemy resolver that queries only the exact identity triple and active mappings.
- [x] Add unit tests for active resolution, unknown issuer/subject/tenant key, inactive mapping, and duplicate identity key. CI Runs #938/#939 passed on Python 3.12 and 3.13 for commit `6a136b38bb4218e39742cfa8063c3050bc8ba705`.
- [x] Verify initial OIDC adapter suite on Python 3.12 and 3.13 — Runs #890/#891 passed for commit da5ead3c81e3cd170536d1dda1d6e9b4a915dfcc.
- [x] Run migration upgrade/downgrade/upgrade and `alembic check` in CI; PostgreSQL integration and full suite passed on Python 3.12/3.13 in Runs #938/#939.
- [x] Verify initial RBAC unit/PostgreSQL integration and migration 0011 in CI Runs #959/#960 on Python 3.12/3.13 (182 tests per run).
- [x] Verify permission-gated history, memory, and work-queue routes plus read-only reviewer grants in CI Runs #967/#968 on Python 3.12/3.13 (184 tests per run).
- [x] Verify four-eyes approval enforcement and migration 0013 on Python 3.12/3.13 in CI Runs #995/#996 (200 tests per run).
- [ ] Choose and configure the actual issuer, audience, JWKS URL, and tenant claim for the deployment.
- [x] Wire configured provider and resolver into runtime composition; tests verify HTTP 401 for invalid-signature and valid-but-unmapped bearer tokens.

## Authorization dependency
Tenant-scoped RBAC is now the runtime default through `SQLAlchemyAuthorizationAdapter`, while the `AuthorizationPort` injection seam remains available for external policy adapters. Missing membership/role/permission denies by default. Four-eyes approval is independently enforced and CI-verified. Trusted-environment provisioning operations and deployment-specific OIDC configuration remain open; see `docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md` and `docs/gates/AUDIT_RETENTION_AND_ACCESS_DESIGN_GATE.md`.

## Gate closure
Do not claim deployment authentication complete until deployment-specific configuration is selected, the trusted mapping provisioning workflow is established, and authorization/membership policy is proven. The adapter, resolver, migration, negative-token HTTP tests, and initial RBAC tests passed CI Runs #938/#939 and #959/#960 on Python 3.12/3.13. This does not establish production readiness while trusted provisioning and deployment-specific settings remain open.
