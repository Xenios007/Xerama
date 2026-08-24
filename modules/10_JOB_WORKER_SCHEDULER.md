# Module 10 — Persistent Job Worker & Scheduler

## Mission
Replace synchronous long-running production requests with restart-safe background execution while preserving the existing GenerationJob model.

## Build
Implement the simplest local Trial-01 worker using the database as durable queue unless a compelling repository constraint requires otherwise. Add claiming/lease/heartbeat semantics so two workers cannot execute the same job. Support queued/running/retrying/succeeded/failed/cancelled, retry delay/backoff, dependency jobs, progress/events and graceful restart recovery.

API generation endpoints should enqueue and return job IDs; inspection endpoints expose status/progress. Keep an optional synchronous execution helper for tests/dev.

Support dependency DAGs sufficient for: story -> storyboard -> image QC -> video -> audio -> final QC -> render. Continuity groups can impose ordering while independent shots can execute concurrently within configured limits.

## Tests
Atomic claim, duplicate prevention, crash/recovery, retry/backoff, cancellation, dependencies, concurrency limit and API enqueue/poll flow.

## Acceptance
Closing/restarting the API or worker does not lose production state, and long video generation no longer holds an HTTP request open.

## Agent instructions
Do not add Redis/Celery just for fashion; local-first is the current decision. Update tests/docs/changelog, run suite, commit, proceed to Module 11.