# MODULE-004 — Database & Persistence

**Status:** AUDIT/EXTEND
**Depends on:** 003

## Objective
Make SQLite the reliable Trial-01 source of truth while remaining portable to PostgreSQL.

## Requirements
- Audit SQLAlchemy models and Alembic migrations against domain contracts.
- Persist projects, series, episodes, scenes, shots, canon, jobs, assets, QC and later production entities.
- Add indexes, uniqueness and foreign-key behavior deliberately.
- Use migrations for schema changes; never destructive reset existing data.
- Keep JSON only for genuinely flexible nested data.

## Verification
Migration-upgrade and repository round-trip tests using temporary DBs.

## Done when
All defined canonical state survives restart and schema is migration-managed; full tests pass; commit/push.