# MODULE-024 — Prompt Compiler

**Status:** BUILD
**Depends on:** 023,025,026,027

## Objective
Compile canonical production data into reproducible provider-ready requests without contaminating domain models.

## Requirements
- Combine shot intent, character DNA/references, style, location/props, continuity frame, negative constraints and provider capabilities.
- Version prompt templates/compiler output.
- Apply vertical composition rules automatically.
- Produce provider-neutral intermediate request then adapter-specific payload.

## Verification
Golden prompt fixtures and missing-reference/capability tests.

## Done when
Prompts are centralized, reproducible and swappable by provider; commit/push.