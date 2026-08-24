# MODULE-041 — Job Queue

**Status:** EXTEND
**Depends on:** 004,005

## Objective
Turn persistent GenerationJob records into a real asynchronous local queue.

## Requirements
- Enqueue/dequeue/claim jobs transactionally.
- Preserve required states queued/running/retrying/succeeded/failed/cancelled.
- Priority, dependency and scheduled retry fields where needed.
- Recover abandoned running jobs after restart.

## Verification
FIFO/priority, claim race, retry, cancellation and restart tests.

## Done when
Long media generation no longer has to block an HTTP request; commit/push.