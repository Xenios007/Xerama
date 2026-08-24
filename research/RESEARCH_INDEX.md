# Xerama Research Index

_Last updated: 2026-08-24_

## Research goal

Xerama is a practical attempt to reproduce the already-working AI microdrama production pattern using public knowledge and available commercial/open models. We will begin with free tiers/trials, measure failures, and pay only where tests demonstrate a useful quality/cost improvement.

The documents in this repository are hypotheses and implementation guidance, not immutable specifications. Trial-and-error is expected.

## Core design documents

- `docs/ARCHITECTURE.md` — system architecture
- `docs/ROADMAP.md` — development roadmap
- `docs/STORY_FORMULA.md` — initial microdrama storytelling grammar
- `docs/AI_MODELS.md` — model-role strategy
- `docs/DATA_MODEL.md` — canonical production/story data
- `docs/JSON_CONTRACTS.md` — AI exchange formats
- `docs/WORKFLOW.md` — proposed end-to-end workflow
- `docs/DECISIONS.md` — architecture decision log

## Research documents

- `research/2026_AI_MICRODRAMA_INDUSTRY.md` — market maturity and evidence that AI-native microdrama is already industrialized
- `research/PRODUCTION_PIPELINE_REVERSE_ENGINEERING.md` — reconstructed production workflow
- `research/MODEL_AND_TOOL_LANDSCAPE.md` — model/tool layers and provider-routing strategy
- `research/CHARACTER_CONTINUITY_PLAYBOOK.md` — identity/reference workflow
- `research/TRIAL_01_EXPERIMENT_PLAN.md` — free-first 3-episode pilot plan

## High-confidence findings

The strongest cross-source consensus is:

1. AI microdrama production is already commercially viable at scale.
2. The pipeline matters more than any single model.
3. Character/reference locking is essential.
4. Story/script/shot planning happens before expensive generation.
5. Episodes are assembled from individual generated shots/clips.
6. Image/reference frames are valuable anchors for video.
7. Different video models can be routed to different shot types.
8. Regeneration/retakes must be budgeted and measured.
9. Persistent assets and state are necessary for series consistency.
10. Subtitles/localization are integral to distribution.
11. Production economics improve sharply when assets and workflows are reusable.

## Important uncertainties to test ourselves

- Which free OpenRouter LLMs are best for concept, dialogue, judge, and continuity?
- How much does two-model candidate generation improve story quality?
- Which image generator gives us the best identity lock per dollar?
- Which current video model gives the lowest cost per accepted second for each shot type?
- Is native dialogue/audio good enough, or do we need TTS + lip sync?
- How many reference images are optimal per character/provider?
- What is our real retake rate?
- Can multimodal QC reliably reject bad generations automatically?
- How much human approval is required to reach publishable quality?
- At what point does a paid model materially outperform free/trial alternatives?

## Primary/strong reporting sources

- Reuters — U.S./global microdrama growth and production adoption:
  https://www.reuters.com/business/media-telecom/microdramas-boom-shrinking-hollywood-studios-chase-tiktok-audience-2026-08-18/
- Caixin Global — China AI short-drama production economics/timing:
  https://www.caixinglobal.com/2026-03-17/chinas-short-drama-makers-rush-to-ride-ai-boom-as-production-costs-plunge-102423944.html
- CNA — China AI filmmaking/microdrama adoption:
  https://www.channelnewsasia.com/east-asia/ai-microdrama-china-film-industry-actors-jobs-6229191
- Xinhua — production hubs, AI adoption, usable footage, output:
  https://english.news.cn/20260421/478dab52b4a147ae800b2dbb64bf7626/c.html

## Official model documentation

- Google Veo model docs:
  https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-generate-001
- Google Veo first/last frame generation:
  https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames
- Google Veo reference images:
  https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/use-reference-images-to-guide-video-generation
- OpenRouter catalog:
  https://openrouter.ai/models

## Production/studio workflow sources

These are useful operational sources but can also market their own products/services; claims should be validated during Xerama trials.

- Ogun Studios:
  https://ogunstudios.com/blog/how-to-make-ai-short-drama
  https://ogunstudios.com/blog/how-ai-micro-dramas-are-produced
  https://ogunstudios.com/blog/ai-character-consistency-micro-drama
- MinionArts:
  https://www.minionarts.com/blogs/how-to-make-ai-microdrama-2026-workflow
  https://www.minionarts.com/blogs/how-ai-microdramas-are-made-node-based-pipeline
  https://www.minionarts.com/blogs/ai-microdrama-tool-stack-2026
- Seedance Review workflow:
  https://seedancereview.com/blog/seedance-ai-short-drama-workflow/
- MajoFlow workflow:
  https://majoflow.com/en/resources/ai-video-animation-workflow/
- InVideo microdrama workflow:
  https://invideo.io/blog/ai-micro-drama-script-to-episode/

## Open-source workflow reference

- `clipcurator/ai-short-drama-production-workflows`
  https://github.com/clipcurator/ai-short-drama-production-workflows

This repository contains public templates/workflow material around vertical-drama formats, storyboards, character continuity, and shot packs. We should inspect ideas and patterns, but write Xerama's own implementation rather than copying code/assets with incompatible licensing.

## Community evidence

Community posts are useful for failure modes and hands-on techniques, not authoritative benchmarks.

- Seedance character consistency discussion:
  https://www.reddit.com/r/aivideos/comments/1smtzb9/seedance_20_character_consistency_across_shots/
- AI short-drama asset workflow discussion:
  https://www.reddit.com/r/Seedance_AI/comments/1taqeiv/two_weeks_into_ai_short_drama_the_wall_isnt/

## Research rule for coding phase

When implementation starts, every external model/provider integration should be treated as an adapter behind a Xerama capability contract. No production workflow should depend on one vendor continuing to expose today's exact model/version.
