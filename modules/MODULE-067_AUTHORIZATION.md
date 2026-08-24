# MODULE-067 — Authentication / Authorization

**Status:** BUILD/LATE
**Depends on:** 066

## Objective
Add identity and authorization when Xerama moves beyond trusted single-user local mode.

## Requirements
- Keep local single-user mode simple but design auth boundary explicitly.
- For hosted mode support users/sessions and project ownership/roles.
- Enforce authorization server-side on project/assets/jobs/reviews.
- Avoid building custom cryptography.

## Verification
Unauthenticated/unauthorized/owner-role tests in hosted mode.

## Done when
Hosted deployments cannot access another user's production through guessed IDs; commit/push.