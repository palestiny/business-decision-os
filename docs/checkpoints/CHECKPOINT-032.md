# CHECKPOINT-032

## Scope

Operational hardening slice 1: make tenant and correlation context explicit in transactional outbox records.

## Status

PASS — CI verified.

## Implemented

- Outbox messages now carry explicit tenant context.
- Outbox messages now carry the command correlation identifier.
- Persisted outbox records expose the same metadata.
- Migration 0007_outbox_operational_metadata adds indexed metadata columns.
- PostgreSQL integration coverage proves metadata survives persistence and publication lookup.

## Why

Audit records already preserved tenant and correlation context, but the transactional outbox did not make that context part of its record contract. That created an operational diagnosis gap: an event could be traced through audit but not directly correlated from the outbox record.

The change keeps the existing transactional-outbox architecture and adds only metadata required for operational traceability.

## Compatibility

The migration columns are nullable so existing outbox rows can remain readable during rollout. New application-generated outbox records populate both fields.

## Verification

CI must verify:

- migration upgrade/downgrade/upgrade;
- schema drift;
- full pytest;
- Python 3.12 and 3.13;
- PostgreSQL integration tests.

## Next

After CI is green, continue the hardening gate with cross-tenant negative tests and explicit HTTP/reliability error-contract coverage. Do not add observability infrastructure or new business capabilities.
