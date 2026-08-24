# Module 09 — Audio, Voice & Lip-Sync Production

## Mission
Implement provider-neutral dialogue/audio production without coupling Xerama to one video model's native speech.

## Build
Support `native`, `tts_lipsync`, and `hybrid` audio modes. Add persistent voice profiles for characters, pronunciation metadata, dialogue segments, audio assets, ambience/SFX/music references and lip-sync jobs/results.

Define `VoiceProvider` and `LipSyncProvider` contracts plus fakes. Preserve exact script text for controlled dialogue. Hybrid mode should allow native ambience while replacing/overlaying controlled speech later in the editor.

Add subtitle/caption timing data as structured artifacts; final burn-in belongs to Module 12.

## Tests
Voice identity selection, dialogue segmentation, mode routing, fake TTS/lipsync, asset lineage, exact text preservation and retry/failure paths.

## Acceptance
An accepted shot can resolve its audio strategy and produce durable dialogue/audio/lipsync assets without vendor-specific logic in the Director.

## Agent instructions
Add migrations/APIs/tests/docs/changelog, run suite, commit, proceed to Module 10.