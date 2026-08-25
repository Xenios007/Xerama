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

- **Story Engine** — concepts, characters, conflicts, secrets, arcs, reveals, hooks, and cliffhangers.
- **Multi-Model Generation** — generates independent candidates and uses an AI judge to select or merge the strongest material.
- **Series State & Continuity** — maintains canonical character knowledge, relationships, secrets, timeline, locations, wardrobe, props, injuries, and previous events.
- **Director Engine** — converts approved scripts into scenes, shots, camera instructions, actions, expressions, and generation prompts.
- **Media Engine** — planned provider-independent layer for image, video, voice, lip sync, music, sound effects, and subtitles.
- **Quality Control** — evaluates story quality, continuity, repetition, production feasibility, and eventual retention potential.

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

## Development Roadmap

### Phase 1 — Story Engine
Idea → multiple concepts → AI judge → series bible → characters → season arc → episode outlines → scripts → continuity validation.

### Phase 2 — Director Engine
Approved script → scenes → shots → storyboards → generation prompts.

### Phase 3 — Media Engine
Character and environment references → video → voice → lip sync → music → SFX → subtitles.

### Phase 4 — Automated Production
End-to-end generation of production-ready vertical microdrama episodes.

### Phase 5 — Analytics & Learning
Use audience performance data to improve hooks, pacing, reveals, cliffhangers, episode length, and future story decisions.

## First Milestones

- **XER-001** — Core Architecture & OpenRouter Model Gateway
- **XER-002** — Multi-Model Concept Generator
- **XER-003** — AI Judge & Candidate Selection
- **XER-004** — Series Bible & Canonical State
- **XER-005** — Character & Relationship Engine
- **XER-006** — Season / Reveal Architecture
- **XER-007** — Episode Beat & Script Engine
- **XER-008** — Continuity Validator
- **XER-009** — Scene & Shot Planner
- **XER-010** — Story Quality Scoring

## Deployment

See `docs/DEPLOYMENT.md` for local/container setup, environment
separation, and the hosted (PostgreSQL/object storage) path.

## Status

Early architecture and research stage.

---

**Xerama** — *Xenios + Drama*