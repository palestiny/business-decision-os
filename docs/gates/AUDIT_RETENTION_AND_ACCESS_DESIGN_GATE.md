# Audit Retention and Access Design Gate

## Status

**OPEN — OPERATING POLICY REQUIRED BEFORE PRODUCTION ROLLOUT.**

Business Decision OS currently persists two separate audit streams:

- `authorization_decision_audit`: one durable ALLOW/DENY record for each completed authorization evaluation.
- `authorization_admin_audit`: durable records for offline identity, membership, and role provisioning/revocation.

Both contain internal identifiers and operational metadata. They must not become a public cross-tenant data source. The code deliberately does not expose an audit-query API. This gate defines retention, access, backup/restore, and deletion controls; it does not claim that any option is a legal requirement.

## Non-negotiable invariants

- Audit records are not deleted or rewritten by ordinary application workflows.
- No public or tenant-facing audit-query endpoint is added until its authorization, tenant scoping, pagination, and data-exposure contract is designed and tested.
- Cross-tenant audit access is restricted to explicitly authorized security/operations personnel and is itself auditable.
- Tenant administrators must never gain cross-tenant audit visibility.
- Audit rows must not contain bearer tokens, raw JWT claims, authorization headers, or request bodies.
- Retention and backup policies are documented deployment configuration, not hidden application behavior.
- Any retention cleanup or archive operation must be controlled, repeatable, observable, and unable to silently erase records under legal hold or active investigation.
- Restore procedures must preserve audit integrity and be tested, not merely assumed from backup configuration.

## Retention options

| Option | Policy | Benefits | Risks / costs |
|---|---|---|---|
| A. Short online window | 90 days searchable, then delete unless explicitly held | Lowest storage cost and data footprint | May be insufficient for delayed fraud, dispute, or incident investigations |
| B. Balanced default | 365 days searchable; any longer archive is deployment/customer-policy driven, encrypted, access-controlled, and subject to documented deletion/legal-hold rules | Useful investigation window without silently imposing indefinite retention; straightforward initial SaaS default | Requires explicit deployment configuration and a controlled retention process |
| C. Long retention | Seven years online or archived | Long investigation history | Higher cost, broader exposure window, and possible conflict with data-minimization expectations or customer commitments |

**Recommendation: Option B.** Treat 365 days as a proposed product default, not a statement of law. Before deployment, review customer contracts and applicable jurisdictional requirements. Do not add automatic row deletion until the policy and legal-hold behavior are approved.

## Access options

| Option | Policy | Benefits | Risks / costs |
|---|---|---|---|
| A. Database operator only | No product API; access through restricted operational database credentials | Smallest exposed surface | Tenant-level self-service investigation is unavailable |
| B. Split tenant and security access | Initially, no audit-query API; restricted security/operations operators may query through approved tooling. If a tenant-facing view is later added, it uses a dedicated permission and strict tenant scoping; platform security access is separate and audited | Separates tenant visibility from platform-wide incident response | Requires privileged-access governance and audit-query design before product UX is added |
| C. Tenant Admin access to all audit | Tenant admins can inspect all audit rows | Simple for support | Unsafe cross-tenant exposure; **rejected** |

**Recommendation: Option B.** Until a protected query interface exists, only approved operations/security personnel should have direct audit access. Application/runtime credentials should not be reused for routine human investigation. Tenant Admin remains tenant-scoped and must never have platform-wide access.

## Backup, restore, and integrity

1. Configure encrypted backups and point-in-time recovery according to the selected database provider and deployment risk.
2. Document backup retention separately from logical audit retention; backup expiry must not be presented as the same thing as audit-row deletion.
3. Restrict database roles so routine runtime operations do not require broad schema-administration privileges. Review whether audit writes can be isolated from audit-reading privileges.
4. Define recovery objectives (RPO/RTO) for audit evidence alongside the main Decision OS database.
5. Test restoration into an isolated environment and verify both audit streams, indexes, timestamps, and correlation links survive.
6. Record retention/cleanup/archive job executions in an operational audit log, including actor/service identity, scope, outcome, and correlation ID.
7. Do not implement a public deletion endpoint or ad hoc SQL cleanup instructions as the normal retention mechanism.

## Decisions required

- [ ] Approve Option B for retention: 365 days searchable by default; longer archive only when deployment/customer/legal policy requires it.
- [ ] Approve Option B for access: restricted security/operations access now; any future tenant-facing audit reader is a separate, tenant-scoped feature.
- [ ] Confirm that retention cleanup remains disabled until legal-hold, archive, and deletion behavior are designed.
- [ ] Select deployment backup provider and set encrypted backup/PITR retention plus RPO/RTO before production launch.
- [ ] Decide whether audit storage/read privileges should be split into separate database roles in the production deployment.

## Acceptance criteria before PASS

- Approved retention duration, archive/deletion behavior, and legal-hold policy are documented.
- Approved audit-reader identities, tenant scoping, privileged access, and access-review cadence are documented.
- No public audit-query endpoint exists without its own API security design and tests.
- Backup encryption, retention, restore ownership, RPO/RTO, and restore verification are evidenced in deployment runbooks.
- Retention or archive jobs are dry-run capable, auditable, and tested against legal holds and active investigations.
- Runtime and administrative credentials follow least privilege; audit evidence is not routinely accessible to ordinary tenant administrators.
- CI and deployment verification prove any implemented retention or access controls; documentation alone is not treated as implementation evidence.

## Dependencies

- `docs/gates/AUTHORIZATION_DECISION_AUDIT_DESIGN_GATE.md`
- `docs/gates/TRUSTED_AUTHORIZATION_PROVISIONING_DESIGN_GATE.md`
- `docs/gates/DEPLOYMENT_AUTHENTICATION_DESIGN_GATE.md`
- `docs/gates/RUNTIME_COMPOSITION_DESIGN_GATE.md`

Do not mark the authorization or runtime gate PASS merely because the audit tables and write path exist.
