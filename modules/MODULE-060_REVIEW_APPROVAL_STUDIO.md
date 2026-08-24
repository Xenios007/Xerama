# MODULE-060 — Review / Approval Studio

**Status:** BUILD
**Depends on:** 044,047,055

## Objective
Centralize human approval for exceptions and publish gates.

## Requirements
- Queue WARN/BLOCK/awaiting-review items.
- Compare takes/versions and display QC evidence/recommendations.
- Approve/reject/request-retake with reason.
- Final episode publish approval must be explicit and auditable.

## Verification
Review queue, decision persistence and permission-ready workflow tests.

## Done when
Human intervention is focused on exceptions instead of manually checking every pipeline step; commit/push.