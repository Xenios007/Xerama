# MODULE-051 — Project API

**Status:** AUDIT/EXTEND
**Depends on:** 009,012,047

## Objective
Expose stable CRUD/control endpoints for project lifecycle.

## Requirements
- Create/list/get/update/archive projects.
- Return current series/production status and active version IDs.
- Validate edits against locked/published state.
- Use domain/service layer, not direct ORM in routes.

## Verification
HTTP happy/error/validation/persistence tests.

## Done when
Frontend can manage project lifecycle entirely through documented API; commit/push.