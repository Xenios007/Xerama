# Xerama Implementation Modules

These files are executable implementation briefs for Codex/Claude Code. Run them in numeric order unless a module explicitly says it may run in parallel.

## Audit baseline — 2026-08-25

Already substantially implemented: project/backend skeleton, SQLite/Alembic persistence, domain contracts, OpenRouter LLM provider, dual concept generation, judge/merge, Series Bible, character text layer, episode outlines, Episode 1 script, shot plan, deterministic retention/continuity validation, canon commit, FastAPI/CLI, persistent stage jobs, and tests.

Partially implemented: character identity, provider health/fallback, persistent jobs.

Missing for finished production: season/reveal planning, full multi-episode generation, production-grade Director/prompt compiler, asset/storage layer, character casting studio, Style Bible/storyboard/image production, media-provider registry, video generation, audio/lipsync, background worker scheduler, multimodal QC/retakes, FFmpeg editor/export, frontend studio, cost/telemetry/analytics, and production hardening.

## Execution order

1. `01_SEASON_REVEAL_ENGINE.md`
2. `02_MULTI_EPISODE_ENGINE.md`
3. `03_DIRECTOR_PROMPT_COMPILER.md`
4. `04_ASSET_STORAGE.md`
5. `05_CHARACTER_CASTING_STUDIO.md`
6. `06_STYLE_STORYBOARD_IMAGE.md`
7. `07_MEDIA_PROVIDER_ROUTER.md`
8. `08_VIDEO_PRODUCTION.md`
9. `09_AUDIO_PRODUCTION.md`
10. `10_JOB_WORKER_SCHEDULER.md`
11. `11_MULTIMODAL_QC_RETAKES.md`
12. `12_EDITOR_EXPORT.md`
13. `13_FRONTEND_STUDIO.md`
14. `14_COST_ANALYTICS_HARDENING.md`

## Agent rule

For every module: read repository docs and current code first; do not duplicate existing implementations; preserve provider independence; use migrations for schema changes; add tests; run the full test suite; update `docs/IMPLEMENTATION_STATUS.md` and `CHANGELOG.md`; make logical commits; continue until the module acceptance criteria pass. Do not wait for perfect provider choices—use interfaces/fakes where credentials or paid providers are unavailable.
