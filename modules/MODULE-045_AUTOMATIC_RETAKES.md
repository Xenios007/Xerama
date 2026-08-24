# MODULE-045 — Automatic Retakes

**Status:** BUILD
**Depends on:** 030,043,044

## Objective
Automatically repair failed assets at the smallest sensible scope.

## Requirements
- Map QC failure types to repair actions: stronger refs, prompt repair, alternate provider, full retake; segment retake optional later.
- Preserve all takes and rejection reasons.
- Enforce retry/cost limits.
- Escalate repeated failure to human review rather than loop forever.

## Verification
Failure-to-action routing, retry budget and lineage tests.

## Done when
Common QC failures self-heal without regenerating unrelated episode work; commit/push.