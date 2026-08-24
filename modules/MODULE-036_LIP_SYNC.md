# MODULE-036 — Lip Sync

**Status:** BUILD
**Depends on:** 032,035,031

## Objective
Synchronize controlled dialogue with visible speaking characters when native audio is insufficient.

## Requirements
- LipSyncProvider interface + fake provider.
- Validate visible speaker, face suitability, input audio/video and duration.
- Persist derived clip as a new asset/take; retain source video/audio.
- Route failures to retry/QC without corrupting originals.

## Verification
Eligibility, fake sync, lineage and failure tests.

## Done when
TTS dialogue can become a versioned lip-synced clip behind a replaceable provider contract; commit/push.