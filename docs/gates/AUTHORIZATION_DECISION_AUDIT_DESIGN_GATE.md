# Authorization Decision Audit Design Gate

## Status

**OPTION B IMPLEMENTED AND VERIFIED IN CI — OPERATING-POLICY CLOSURE PENDING.**

The tenant-scoped RBAC adapter now evaluates active actor, membership, role assignment, role, and permission records and writes a durable PostgreSQL audit row for each completed allow/deny evaluation. Trusted provisioning changes remain in the separate administration audit.

## Security objective

Make it possible to reconstruct which actor was allowed or denied a protected operation, for which tenant, permission, and resource, without storing bearer tokens, raw claims, or other authentication secrets. Audit failure must never silently turn into authorization success.

## Options

| Option | Behavior | Benefits | Risks / costs |
|---|---|---|---|
| A. Application logs only | Emit structured allow/deny logs | Lowest implementation cost | Log retention/access is deployment-dependent; events may be dropped and are harder to query transactionally; not sufficient as the durable authorization audit |
| B. Append-only PostgreSQL decision audit | Persist one row for each completed allow/deny check; commit the audit row before returning success or raising a policy denial | Durable, queryable, supports investigation and tenant-scoped reporting; aligns with current database-backed RBAC | Adds a write and latency to every authorization check; audit storage failure must fail closed |
| C. Asynchronous external event pipeline | Publish authorization events to a durable external sink | Better scale and separation from the OLTP database | Requires an outbox or reliable delivery path, operational dependencies, and a clear policy for authorization when the pipeline is unavailable; defer until scale evidence warrants it |

## Recommended contract (Option B)

1. Add authorization_decision_audit as a separate append-only-by-application table; do not mix access-decision events with authorization_admin_audit.
2. Record actor_id, tenant_id, permission, resource_id, outcome (ALLOW / DENY), a bounded reason_code, UTC occurred_at, and optional correlation_id.
3. For a completed policy evaluation, perform the policy query and insert the audit record within one short database transaction. Commit before returning from require.
4. On a denied decision, commit the DENY record first, then raise AuthorizationDenied. Do not raise inside the transaction before commit, or the denial record would roll back.
5. If the policy query or audit insert/commit fails, raise PolicyEvaluationUnavailable; never return an allow without a committed audit row. If the database itself is unavailable, a durable audit row cannot be guaranteed; emit a structured error log and deny.
6. Use generic denial reason codes (for example PERMISSION_NOT_GRANTED) rather than disclosing whether a user, membership, role, or permission row was missing to an untrusted caller.
7. Never record bearer tokens, full JWT claims, authorization headers, raw request bodies, or sensitive resource contents. Store only stable internal IDs and policy metadata.
8. Keep authorization decisions uncached. Every protected request evaluates current membership/role state and writes a fresh audit row, so revocation remains effective on the next check.
9. Add indexes suitable for investigation by tenant/time, actor/time, resource, and correlation ID. Do not add public audit-query endpoints in this slice.
10. Keep retention duration, backup/restore policy, and privileged audit-reader access explicit deployment decisions; do not silently delete records in application code.

## Acceptance criteria

- [x] Product owner approved Option B.
- [x] Added `authorization_decision_audit`, separate from administrative provisioning audit, with actor/tenant/permission/resource/outcome/reason/time/correlation and investigation indexes.
- [x] Policy evaluation and audit insert commit in one transaction; a denial is raised only after its DENY audit row commits.
- [x] Audit insert/commit failure and policy-store failure raise `PolicyEvaluationUnavailable`; no allow is returned without a committed audit.
- [x] Generic reason codes avoid revealing which RBAC layer was missing; no credentials or raw JWT claims are recorded.
- [x] Unit tests cover allow, deny, audit failure, and policy-store failure.
- [x] PostgreSQL integration covers durable allow/deny rows and actor/tenant/resource/correlation attribution.
- [x] Migration lifecycle, `alembic current --check-heads`, `alembic check`, and CI verification on Python 3.12/3.13 — Runs #1011/#1012 passed for the durable audit slice; command-correlation propagation then passed Runs #1023/#1024 with 204 tests per run.
- [x] Request correlation IDs propagate from protected API commands into authorization decision audit rows; unit/API contract tests verify the path.
- [ ] Retention, backup/restore, and privileged-reader access remain deployment decisions before production rollout.
- [ ] Retention, backup/restore, and privileged-reader access remain deployment decisions before production rollout.

## Dependencies

- docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md
- docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md
- docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md
- docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md

Do not mark the overall authorization or runtime gate PASS merely because the decision-audit adapter exists. Production operations, retention, and privileged audit access remain separate deployment controls.
