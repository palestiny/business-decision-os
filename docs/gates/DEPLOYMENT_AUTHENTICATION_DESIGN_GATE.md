# Deployment Authentication Design Gate

## Status
**OIDC/JWT ADAPTER IMPLEMENTED — DEPLOYMENT IDENTITY MAPPING AND CI VERIFICATION REMAIN OPEN.** The provider validates configured RS256 bearer tokens and delegates verified external identity mapping; it is not yet a complete deployment configuration.

## Security invariants
- Requests without valid authenticated identity fail closed.
- Actor identity is derived from a verified identity, never from a request body or arbitrary header.
- Tenant identity comes from a verified, trusted identity claim or a server-side identity-to-tenant mapping. A client-supplied tenant ID is never authoritative.
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

## Decisions still required before implementation
- Identity provider and issuer URL.
- Expected audience/resource identifier.
- Which verified claim or server-side mapping identifies the tenant.
- Which verified subject maps to the internal actor UUID.
- Whether this first deployment is public SaaS or behind a private trusted proxy.

## Implementation status
- [x] Add an OIDC/JWT PrincipalProvider adapter with explicit issuer, audience, JWKS URL, tenant-claim name, and external identity resolver.
- [x] Restrict token verification to RS256 and validate signature, issuer, audience, expiry, issued-at, and required subject/tenant claims; reject missing bearer credentials and unmapped identities.
- [x] Keep external subject/tenant keys separate from internal UUIDs through an explicit resolver contract.
- [x] Add unit tests for valid identity mapping, missing/non-bearer credentials, wrong issuer/audience, expired tokens, missing claims, unknown identity mapping, and invalid signatures.
- [ ] Confirm the new adapter test suite in CI on Python 3.12 and 3.13.
- [ ] Choose and configure the actual issuer, audience, JWKS URL, and tenant claim for the deployment.
- [ ] Implement and test a production-grade external identity resolver backed by the chosen identity/tenant model.
- [ ] Add runtime composition wiring for the concrete configured provider and test HTTP rejection for invalid bearer tokens.

## Gate closure
Do not claim deployment authentication complete until deployment-specific configuration, production identity mapping, negative-token tests, and tenant-spoofing tests pass in CI. The adapter is a security boundary component, not a ready-to-deploy identity system; `build_runtime_app` still requires explicit provider injection.
