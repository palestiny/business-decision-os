# Authorization Decision Audit Design Gate

## Status

**OPEN — RECOMMENDED OPTION B: DURABLE DATABASE AUDIT FOR EACH COMPLETED ALLOW/DENY DECISION.**

The tenant-scoped RBAC adapter currently evaluates active actor, membership, role assignment, role, and permission records. Denials are written to application logs, while trusted provisioning changes have a separate durable administration audit. There is not yet a durable record for every authorization decision, including successful grants.

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

- [ ] Product owner approves Option B or chooses A/C.
- [ ] Every completed authorization allow and deny has one durable row.
- [ ] Denial audit commits before AuthorizationDenied is raised.
- [ ] Audit insertion/commit failure causes fail-closed PolicyEvaluationUnavailable.
- [ ] Policy-store unavailability also fails closed and emits a structured operational log.
- [ ] Audit rows contain no bearer tokens or raw JWT claims.
- [ ] Unit tests cover allow, deny, generic reason codes, audit failure, and policy-store failure.
- [ ] PostgreSQL integration verifies durable allow/deny rows, transaction behavior, and tenant/resource attribution.
- [ ] Migration upgrade/downgrade/upgrade and alembic check pass.
- [ ] CI passes on Python 3.12 and 3.13.
- [ ] Retention and privileged-reader access are documented before production rollout.

## Dependencies

- docs/gates/AUTHORIZATION_MODEL_DESIGN_GATE.md
- docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md
- docs/gates/SEPARATION_OF_DUTIES_DESIGN_GATE.md
- docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md

Do not mark the overall authorization or runtime gate PASS merely because the decision-audit adapter exists. Production operations, retention, and privileged audit access remain separate deployment controls.
