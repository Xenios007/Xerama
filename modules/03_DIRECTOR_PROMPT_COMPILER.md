# Module 03 — Director & Prompt Compiler

## Mission
Turn the existing basic shot planner into a production-grade, provider-neutral Director.

## Build
Extend shot contracts only where necessary for shot size, angle, lens, camera movement, blocking, composition, lighting, narrative function, dialogue coverage, vertical safe area, continuity group, required references, provider capability requirements and optional temporal micro-beats.

Implement deterministic directing passes for 9:16 composition, dialogue coverage, runtime budget and continuity grouping. Add a provider-neutral Prompt Compiler that combines shot intent + Character DNA/references + Style Bible + location/props + continuity frame + negative constraints into an intermediate generation request.

Provider-specific adapters later translate that request into vendor payloads. Do not put Runway/Kling/Veo/etc. syntax into domain models.

## Tests
Shot-contract validation, dialogue coverage, vertical composition, prompt compilation determinism, reference selection and continuity groups.

## Acceptance
Every approved script can compile into media-ready structured shots without knowing the final image/video vendor.

## Agent instructions
Read `research/WIND_COMIC_DEEP_DIVE.md`, `research/PRODUCTION_STACK_2026.md`, current `shot_stage` and scene schemas. Avoid overengineering spatial blocking V1. Update migrations/docs/tests/changelog, run suite, commit, proceed to Module 04.