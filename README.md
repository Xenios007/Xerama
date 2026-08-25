# Xerama

**Xenios + Drama**

Xerama is an AI-powered microdrama creation and production system designed to transform a story idea into a coherent serialized vertical drama.

## Vision

Build an AI-native microdrama studio capable of taking a concept from story development through production while preserving narrative quality, character consistency, continuity, and production control.

## Target Pipeline

```text
Idea
  ↓
Multi-Model Concept Generation
  ↓
AI Judge / Selection / Merge
  ↓
Series Bible
  ↓
Character & World Bible
  ↓
Season Architecture
  ↓
Episode Planning
  ↓
Script Generation
  ↓
Continuity Validation
  ↓
Scene & Shot Planning
  ↓
Visual / Video Generation
  ↓
Voice + Music + SFX + Subtitles
  ↓
Automated Editing
  ↓
Quality Control
  ↓
Final 9:16 Microdrama Episode
```

## Core Systems

Everything below is implemented (`docs/IMPLEMENTATION_STATUS.md` has the
per-module detail) and runnable end to end today without any paid API
key - every external provider (LLM/image/video/voice/lip-sync/vision-QC)
follows a "contract + fake now, real adapter later" pattern: a typed
Protocol, a fake/deterministic implementation used by default and by the
entire test suite, and a slot for a real adapter that swaps in without
touching pipeline code.

- **Story Engine** — concepts, characters, conflicts, secrets, arcs, reveals, hooks, and cliffhangers.
- **Multi-Model Generation** — generates independent candidates and uses an AI judge to select or merge the strongest material.
- **Series State & Continuity** — maintains canonical character knowledge, relationships, secrets, timeline, locations, wardrobe, props, injuries, and previous events.
- **Director Engine** — converts approved scripts into scenes, shots, camera instructions, actions, expressions, and generation prompts.
- **Media Engine** — provider-independent contracts for image, video, voice, lip sync, music, sound effects, and subtitles, with QC gating and automatic-retake escalation.
- **Production Platform** — job queue/worker, FFmpeg assembly, episode versioning, vertical export, cost tracking, observability, and a React studio UI (dashboard, story, character, production, review).
- **Quality Control** — evaluates story quality, continuity, repetition, production feasibility, and retention/eval benchmarking (both AI-role and media-provider evaluation harnesses).

## Initial AI Strategy

Xerama will begin with OpenRouter and free models. The default development mode produces at least two independent candidates and sends them to a judge that can choose Candidate A, Candidate B, or request a merge.

```text
                 Request
                    │
          ┌─────────┴─────────┐
          ↓                   ↓
      Model A             Model B
    Candidate A         Candidate B
          │                   │
          └─────────┬─────────┘
                    ↓
                 AI Judge
                    ↓
            A / B / Merge
                    ↓
             Approved State
```

Model identifiers are configuration rather than application logic so providers and models can be changed without rewriting the story engine.

## Quickstart

```bash
# Backend
python -m venv .venv && source .venv/bin/activate   # Scripts/activate on Windows
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn xerama.api.app:app --reload

# Frontend (separate terminal)
cd frontend && cp .env.example .env && npm install && npm run dev
```

`GET /health` (liveness) and `GET /health/ready` (DB reachability) are
available immediately. No `OPENROUTER_API_KEY` is required to run the
full pipeline - every stage works against fake/free-tier defaults; see
`docs/DEPLOYMENT.md` for the full runbook (container path, environment
separation, backup/restore, hosted-deployment path).

## Testing

```bash
pytest -q                 # every backend test (unit + integration + e2e)
pytest -m e2e -q          # the single full brief-to-rendered-episode flow
cd frontend && npm test -- --run
```

See `docs/TESTING.md` for the full test-architecture map (unit/
integration/E2E boundaries, fake-provider inventory, coverage).

## Documentation

| Doc | Covers |
|---|---|
| `docs/IMPLEMENTATION_STATUS.md` | What is actually built, module by module - the live source of truth. |
| `docs/ARCHITECTURE.md` | System design: layering, data flow, quality gates, job/asset model. |
| `docs/DECISIONS.md` | Numbered ADRs - the *why* behind cross-cutting choices. |
| `docs/DATA_MODEL.md` / `docs/JSON_CONTRACTS.md` | Persisted entities and the structured-output schemas every AI role must return. |
| `docs/DEPLOYMENT.md` | Local/container setup, environment separation, backup/restore, hosted-deployment path. |
| `docs/TESTING.md` | Test-architecture map: layers, fixtures, fake providers, coverage. |
| `docs/AI_MODELS.md` | Model-role assignments and free-tier defaults. |
| `docs/WORKFLOW.md` / `docs/STORY_FORMULA.md` | The creative pipeline stages and the storytelling heuristics behind them. |
| `modules/README.md` | The authoritative MODULE-001..080 implementation queue and its execution rules. |
| `CHANGELOG.md` | Chronological log of what changed and why, per module. |
| `docs/ROADMAP.md` | **Superseded** - kept for historical context; see `modules/README.md` and `docs/IMPLEMENTATION_STATUS.md` instead. |

## Status

Active implementation against the MODULE-001..080 architecture queue
(`modules/README.md`) - most of the queue is implemented and tested.
`docs/IMPLEMENTATION_STATUS.md`'s header states exactly which module was
completed most recently and lists what remains genuinely partial (real
paid provider adapters behind the existing contracts, PostgreSQL/
object-storage behind the existing repository/storage interfaces) - it
is the live source of truth for "what's actually done," not this file.

---

**Xerama** — *Xenios + Drama*