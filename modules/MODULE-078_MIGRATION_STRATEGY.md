# MODULE-078 — Migration Strategy

**Status:** BUILD
**Depends on:** 004,005,040

## Objective
Make future SQLite→PostgreSQL and local→object-storage transitions deliberate and testable.

## Requirements
- Keep domain/repository/storage interfaces portable.
- Document data export/import and asset-key mapping.
- Avoid SQLite-only semantics in application logic.
- Add compatibility checks/migration tooling only when justified.

## Verification
Repository contract tests and portable schema review; optional PostgreSQL CI when configured.

## Done when
Hosted scaling does not require rewriting story/production services; commit/push.