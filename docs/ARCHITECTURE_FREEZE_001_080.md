# Xerama Architecture Freeze — MODULE-001..080

_Date: 2026-08-25_

The repository has been audited against the finished-system architecture. Before this freeze, `modules/` contained 14 implementation briefs covering major missing production areas. They were useful but did not constitute a complete executable architecture queue.

The authoritative plan is now `modules/README.md` plus the individual `modules/MODULE-001_*.md` through `MODULE-080_*.md` files. These cover foundation, story/canon, directing, character/style/reference systems, image/video/audio, storage/jobs/QC/editor, APIs/frontend, analytics/learning, security/deployment, testing/recovery/migrations and release operations.

Existing code must be audited and extended rather than rewritten. At freeze time the repository already reported a working Python/FastAPI/Pydantic/SQLAlchemy/Alembic foundation, OpenRouter + fake LLM provider, role configuration, AI gateway, dual-candidate/judge/merge story flow, Series Bible/cast/outlines, Episode 1 script/shot plan, deterministic retention/continuity validators, targeted shot-plan retry, canon commit, persistent stage jobs, API/CLI and 39 tests. The module queue deliberately marks these early areas AUDIT/EXTEND.

The major unfinished path begins with season/reveal depth, full multi-episode scripts, production directing, persistent media assets, synthetic visual casting, Style Bible/storyboards, media provider routing, image/video/audio generation, background workers, multimodal QC/retakes, FFmpeg export, frontend studio, analytics/cost, security/deployment and release hardening.

Claude/Codex should use the module queue continuously and may leave only optional live-provider verification pending when credentials are unavailable. Fake-provider correctness and complete architecture wiring remain mandatory.