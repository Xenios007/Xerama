# Module 07 — Media Provider Registry & Router

## Mission
Generalize provider routing beyond the existing single OpenRouter LLM provider.

## Build
Create capability contracts/registries for image, video, voice and lip-sync providers. Providers declare supported operations, references, aspect ratios, duration/resolution limits, native audio and other relevant capabilities. Implement eligibility filtering, health/circuit state, fallback order and policy hooks for quality/cost/latency.

Do not hardcode today's vendor/model list in business logic. Configuration owns provider/model IDs. Add fake providers for every media type and at least one real adapter only where credentials/API access are practical.

Record fallback reason and selected capability path. Preserve current OpenRouter behavior.

## Tests
Capability filtering, incompatible request rejection, health circuit behavior, fallback, deterministic policy ordering and fake-provider end-to-end generation.

## Acceptance
A media request asks Xerama for capabilities, not a vendor, and the router can choose/fallback among registered providers.

## Agent instructions
Reuse current provider error/health abstractions instead of creating a second system. Update docs/tests/changelog, run suite, commit, proceed to Module 08.