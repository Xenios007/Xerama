# Xerama Research Index

_Last updated: 2026-08-24_

## Research goal

Xerama is a practical attempt to reproduce the already-working AI microdrama production pattern using public knowledge, open-source systems, research papers and available commercial/open models. We will begin with free tiers/trials, measure failures and pay only where tests demonstrate a useful quality/cost improvement.

The documents in this repository are hypotheses and implementation guidance, not immutable specifications. Trial-and-error is expected.

## Current research status

**Core architecture research is now sufficient to begin coding.**

A source-level review of Wind Comic materially reduced uncertainty around specialist-agent orchestration, provider routing, character/style locking, generation jobs, persistent assets, quality loops, retakes, multi-episode memory, cost telemetry and deterministic finishing. Remaining unknowns are mainly empirical model/provider quality and should be answered through benchmarks and Trial 01 rather than more speculative architecture work.

## Core design documents

- `docs/ARCHITECTURE.md` — system architecture, updated with provider routing, production anchors, jobs/assets and QC loops
- `docs/ROADMAP.md` — development roadmap
- `docs/STORY_FORMULA.md` — initial microdrama storytelling grammar
- `docs/AI_MODELS.md` — model-role strategy
- `docs/DATA_MODEL.md` — canonical production/story data
- `docs/JSON_CONTRACTS.md` — AI exchange formats
- `docs/WORKFLOW.md` — proposed end-to-end workflow
- `docs/DECISIONS.md` — architecture decision log, including Wind Comic-derived decisions

## Research documents

- `research/2026_AI_MICRODRAMA_INDUSTRY.md` — market maturity and evidence that AI-native microdrama is already industrialized
- `research/PRODUCTION_PIPELINE_REVERSE_ENGINEERING.md` — reconstructed production workflow
- `research/MODEL_AND_TOOL_LANDSCAPE.md` — model/tool layers and provider-routing strategy
- `research/CHARACTER_CONTINUITY_PLAYBOOK.md` — identity/reference workflow, Character DNA, Style Bible and vision retry
- `research/ACTOR_LIKENESS_AND_CHARACTER_DESIGN.md` — real actors, licensed likeness, synthetic casting, archetype references and rights metadata
- `research/OPEN_SOURCE_SYSTEMS_TO_STUDY.md` — working public systems and architecture patterns to reverse engineer
- `research/WIND_COMIC_DEEP_DIVE.md` — source-level extraction of the strongest working open-source reference found so far
- `research/RESEARCH_PAPERS_AND_BENCHMARKS.md` — DramaDirector, One Sentence One Drama, Co-Director, benchmark lessons
- `research/FREE_FIRST_MODEL_STRATEGY.md` — OpenRouter free/pinned model experiments and paid-model promotion rules
- `research/PRODUCTION_STACK_2026.md` — current LLM/image/video/voice/lipsync/edit/QC stack and provider contracts
- `research/TRIAL_01_EXPERIMENT_PLAN.md` — free-first 3-episode pilot plan
- `research/CODING_READINESS_CHECKLIST.md` — coding gate and remaining empirical selections

## High-confidence findings

1. AI microdrama production is already commercially viable at scale.
2. The pipeline matters more than any single model.
3. Character/reference locking is essential.
4. Character DNA can reinforce visual references across providers/shots.
5. A canonical Style Bible is useful for production-wide visual consistency.
6. Real performers can participate through licensed digital likeness/performance capture, but commercial Xerama should not depend on unauthorized celebrity replicas.
7. Original synthetic performers should be reusable identity assets with permanent root references.
8. Story/script/shot planning happens before expensive generation.
9. Episodes are assembled from individual generated shots/clips.
10. Storyboard/first/reference frames are valuable anchors for video.
11. The actual last frame of a generated clip can improve continuity into the next connected shot.
12. Different video models can be routed to different shot types based on declared capabilities.
13. Provider health/fallback should be part of routing, not an afterthought.
14. Reviewer loops and targeted regeneration are preferable to regenerating whole episodes.
15. Persistent canon, visual assets and state are necessary for series consistency.
16. Deterministic editing is preferable once generated assets are approved.
17. Persistent jobs and asset storage are required for a reliable production system.
18. Benchmark telemetry is required before deciding whether a paid model is worth the cost.
19. Cost per accepted output is more meaningful than raw API price.
20. Multiple open-source projects already implement large parts of the architecture Xerama needs.
21. Wind Comic provides a particularly mature working reference for many of these patterns.
22. Architecture research is no longer the main blocker; empirical model/provider benchmarking is.

## Existing systems that deserve source-level study

Primary reference:
- Wind Comic: https://github.com/ChrisChen667788/wind-comic

Additional systems:
- AI Short Film: https://github.com/wushaojun321/ai-short-film
- StoryMind: https://github.com/LinHao-city/StoryMind
- AI Video Pipeline: https://github.com/0xadvait/ai-video-pipeline
- DramaDirector: https://github.com/iLearn-Lab/DramaDirector
- MovieAgent: https://github.com/showlab/MovieAgent
- Awesome AI Short Drama index: https://github.com/PAMPAS-Lab/awesome-ai-short-drama

## Key research papers

- One Sentence, One Drama: https://arxiv.org/abs/2605.22144
- DramaDirector: https://arxiv.org/abs/2606.24107
- Co-Director: https://arxiv.org/abs/2604.24842
- Agentic Video Generation / GEST: https://arxiv.org/abs/2604.10383

## Actor likeness / digital performer sources

- Shortical / Aki Avni case: https://www.thewrap.com/media-platforms/tv/shortical-ai-generated-microdrama-aki-avni-inevitable-ofir-lobel/
- Reuters / Ironblood real-actor AI production: https://www.reuters.com/business/media-telecom/microdramas-boom-shrinking-hollywood-studios-chase-tiktok-audience-2026-08-18/
- SAG-AFTRA AI TV/Theatrical guidance: https://www.sagaftra.org/sites/default/files/sa_documents/AI%20TVTH.pdf
- California digital-replica protections: https://www.gov.ca.gov/2024/09/17/governor-newsom-signs-bills-to-protect-digital-likeness-of-performers/
- Philippine Digital Likeness and Deepfake Regulation Act proposal: https://senate.gov.ph/legislative-documents/bills/615670

## Official model/platform documentation

- OpenRouter free router: https://openrouter.ai/docs/guides/routing/routers/free-router
- OpenRouter structured outputs: https://openrouter.ai/docs/guides/features/structured-outputs
- OpenRouter model catalog: https://openrouter.ai/models
- Runway References: https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References
- Runway API models: https://docs.dev.runwayml.com/guides/models/
- Google Veo: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-generate-001

## Production/studio workflow sources

These are useful operational sources but can market their own products/services; claims should be validated during Xerama trials.

- Ogun Studios: https://ogunstudios.com/blog/how-to-make-ai-short-drama
- MinionArts: https://www.minionarts.com/blogs/how-to-make-ai-microdrama-2026-workflow
- MinionArts node pipeline: https://www.minionarts.com/blogs/how-ai-microdramas-are-made-node-based-pipeline

## Important uncertainties to test ourselves

- Which free OpenRouter models are best for concept, dialogue, judge and continuity?
- How much does two-model candidate generation improve story quality?
- Which image generator gives the best identity lock per accepted image?
- Which video model gives the lowest cost per accepted second for each shot type?
- Is native dialogue/audio good enough, or do we need TTS + lip sync?
- How many reference images are optimal per character/provider?
- What is our real retake rate?
- Can multimodal QC reliably reject bad generations automatically?
- How much human approval is required to reach publishable quality?
- At what point does a paid model materially outperform free/trial alternatives?

## Research rule for coding phase

When implementation starts, every external model/provider integration should be treated as an adapter behind a Xerama capability contract. No production workflow should depend on one vendor continuing to expose today's exact model/version.

Any external source code reused in Xerama must have its license and exact source commit recorded first.
