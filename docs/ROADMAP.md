# Xerama Development Roadmap

> **Superseded.** This is the original, coarse-grained (XER-001..010 plus
> four "planned" phases) planning document, kept for historical context
> only. It predates and is superseded by `modules/README.md`'s
> authoritative MODULE-001..080 queue, and nearly everything this file
> lists as "planned" is now implemented - see
> `docs/IMPLEMENTATION_STATUS.md` for what is actually built, and
> `README.md` for the current setup/run/test entry points.

## Phase 1 — Story Intelligence

### XER-001 — Core Architecture & OpenRouter Model Gateway
Define architecture, environment configuration, provider abstraction, model roles, retries, logging, and structured AI responses.

### XER-002 — Multi-Model Concept Generator
Generate at least two independent microdrama concepts from the same creative brief.

### XER-003 — AI Judge & Candidate Selection
Score candidates and return `A`, `B`, or `MERGE`, with explicit strengths, weaknesses, and merge instructions.

### XER-004 — Series Bible & Canonical State
Persist the approved premise, world rules, themes, tone, conflicts, secrets, and immutable/locked facts.

### XER-005 — Character & Relationship Engine
Create characters, motivations, flaws, relationships, knowledge state, secrets, and long-term character arcs.

### XER-006 — Season & Reveal Architecture
Create the macro story arc, escalation ladder, reveal map, mystery/payoff schedule, and episode-level progression.

### XER-007 — Episode Beat & Script Engine
Generate structured episode beats and convert approved beats into short vertical-drama scripts.

### XER-008 — Continuity Validator
Detect contradictions involving chronology, knowledge, relationships, locations, injuries, props, wardrobe, and established canon.

### XER-009 — Scene & Shot Planner
Convert scripts into structured scenes and production-oriented shot lists.

### XER-010 — Story Quality Scoring
Score hooks, conflict, emotional intensity, information gaps, reversals, cliffhangers, repetition, continuity, serial potential, and production feasibility.

## Phase 2 — Directing

Planned capabilities:

- scene blocking
- character positioning
- shot composition
- camera movement
- visual continuity requirements
- storyboard prompts
- model-specific prompt compilation
- reference asset management

## Phase 3 — Media Generation

Planned provider-independent interfaces:

- image generation
- image/reference editing
- video generation
- voice generation
- lip synchronization
- music generation/selection
- sound effects
- subtitles

## Phase 4 — Automated Production

Planned capabilities:

- generation queue
- retries and fallback models
- shot-level QC
- automatic assembly
- dialogue/audio synchronization
- subtitles
- vertical 9:16 export
- episode versioning
- production cost tracking

## Phase 5 — Analytics & Learning

Planned feedback signals:

- impressions
- 3-second retention
- average watch time
- completion rate
- rewatch rate
- skip/drop points
- shares
- comments
- episode-to-episode continuation

The long-term objective is to connect performance patterns back to story decisions without allowing short-term metrics to destroy narrative coherence.
