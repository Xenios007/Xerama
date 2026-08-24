# MODULE-064 — Recommendation / Optimization

**Status:** BUILD
**Depends on:** 049,063

## Objective
Recommend model, routing and production changes using quality, cost and performance evidence.

## Requirements
- Rank providers by shot class using accepted-output rate, cost, latency and QC.
- Suggest story/production experiments separately from automatic canon changes.
- Support configurable optimization objective: quality, budget, speed or balanced.
- Explain evidence behind recommendations.

## Verification
Ranking, sparse-data and objective-switch tests.

## Done when
Recommendations are measurable, reversible and never silently alter creative truth; commit/push.