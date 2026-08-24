# MODULE-034 — Voice Generation

**Status:** BUILD
**Depends on:** 026,031,040

## Objective
Provide stable reusable voices for recurring characters.

## Requirements
- VoiceProvider interface + fake provider.
- Persist voice profile/provider ID, language, style, pronunciation and rights metadata.
- Generate line-level or scene-level audio with timing metadata.
- Never assume cloning rights; provenance is required for external likeness/voice.

## Verification
Voice profile, fake generation, persistence and pronunciation tests.

## Done when
Dialogue audio can be regenerated independently of video while retaining character voice identity; commit/push.