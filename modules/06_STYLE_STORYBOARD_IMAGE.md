# Module 06 — Style Bible, Storyboard & Image Production

## Mission
Build the still-image production stage that solves style/composition/identity before expensive video generation.

## Build
Add dedicated Style Bible persistence: canonical image asset, textual style DNA, palette, lighting, texture, color temperature, composition rules and negatives. Add storyboard/keyframe records linked to shots and asset versions.

Define `ImageProvider` contract and fake implementation. Build workflow: approved shot -> rough storyboard/layout -> compiled references -> final keyframe -> QC state -> accept/retry. Real provider implementation may be added only if a practical free/trial API is available; architecture must work with fake provider tests.

Support manual asset upload as a first-class fallback so the pipeline is not blocked by provider availability.

## Tests
Style persistence/locking, storyboard-to-keyframe lineage, retry/versioning, provider capability rejection and manual upload path.

## Acceptance
Every shot can reach an approved durable first/key frame with character/style/location references before video generation.

## Agent instructions
Read Wind Comic deep dive and production stack. Add migrations/APIs/tests/docs/changelog, run suite, commit, proceed to Module 07.