# MODULE-077 — Backup / Recovery

**Status:** BUILD
**Depends on:** 004,040,047

## Objective
Protect project metadata and media assets from local failure/operator error.

## Requirements
- Document consistent backup of DB plus asset store.
- Provide local backup/restore command or script with manifest/hash validation.
- Preserve version lineage and configuration metadata needed to reopen projects.
- Hosted strategy may document DB/object-store native backups.

## Verification
Backup→delete test copy→restore→integrity verification.

## Done when
A project can be restored to a usable consistent state from documented backup artifacts; commit/push.