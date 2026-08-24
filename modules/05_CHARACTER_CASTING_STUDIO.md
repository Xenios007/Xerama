# Module 05 — Character Casting Studio

## Mission
Upgrade textual characters into reusable production identities while keeping generation provider-neutral.

## Build
Persist root identity asset, multi-view references, Character DNA, wardrobe variants, physical-state variants, voice profile pointer, lock state and provenance/consent metadata. Implement centralized `ConsistencyPolicy` that selects references/DNA/wardrobe/style for a shot within provider reference limits.

Add character asset CRUD/lock/version APIs. Do not implement unauthorized celebrity-cloning workflows. The default production path is original synthetic cast or explicitly authorized/licensed identity assets.

Use fake image providers initially if real image integration belongs to Module 06/07.

## QC hooks
Define identity-QC interface and thresholds but leave multimodal implementation to Module 11.

## Tests
Locked identity immutability, versioning, wardrobe/state selection, multi-character reference selection, provenance requirements and provider max-reference behavior.

## Acceptance
A recurring character has a durable identity package that downstream storyboard/image/video/audio stages can reference consistently.

## Agent instructions
Read `research/CHARACTER_CONTINUITY_PLAYBOOK.md` and actor-likeness research. Add migrations/tests/docs/changelog, run suite, commit, proceed to Module 06.