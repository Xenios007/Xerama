# Xerama Architecture

## 1. Purpose

Xerama is designed as a provider-independent AI microdrama production platform. Story intelligence, canonical series state, directing, media generation, and quality control are separate layers so individual AI providers can be replaced without redesigning the application.

## 2. High-Level Architecture

```text
User / Studio
    ↓
Project Service
    ↓
Showrunner / Story Engine
    ├── Candidate Generator A
    ├── Candidate Generator B
    └── Judge / Merge
    ↓
Canonical Series State
    ├── Series Bible
    ├── Character State
    ├── Relationships
    ├── Knowledge / Secrets
    ├── Timeline
    └── World State
    ↓
Episode Engine
    ├── Beat Planner
    ├── Script Writer
    ├── Retention Critic
    └── Continuity Validator
    ↓
Director Engine
    ├── Scene Planner
    ├── Shot Planner
    └── Prompt Compiler
    ↓
Media Engine
    ├── Image Provider
    ├── Video Provider
    ├── Voice Provider
    └── Audio Provider
    ↓
QC / Editor
    ↓
Final Episode
```

## 3. Architectural Principles

### Canonical state over prompt memory
The database is the source of truth. Models receive only the state needed for their task. Model output does not become canon until validated and committed.

### Provider independence
Application services request capabilities such as `concept_generator`, `episode_writer`, or `continuity_checker`; they should not depend directly on a specific model identifier.

### Structured contracts
Important AI stages return validated structured data instead of unconstrained prose. This enables scoring, retries, comparison, persistence, and downstream automation.

### Generate before spending
Story, continuity, and production-feasibility checks happen before expensive image or video generation.

### Human override
Every major AI decision should eventually support approval, rejection, editing, regeneration, and locking.

## 4. Initial Multi-Model Flow

Standard mode begins with two independent candidates.

```text
Input
  ├── Model A → Candidate A
  └── Model B → Candidate B
                  ↓
                Judge
                  ↓
             A / B / Merge
                  ↓
              Approved
```

The judge evaluates hook strength, emotional intensity, originality, serial potential, reversals, cliffhanger potential, character potential, and production feasibility.

## 5. Model Gateway

The first provider is OpenRouter. Model configuration will be externalized so free and paid models can be benchmarked and replaced without modifying story logic.

Planned logical roles:

- `concept_generator_a`
- `concept_generator_b`
- `story_architect`
- `judge`
- `episode_writer`
- `continuity_checker`
- `retention_critic`
- `shot_planner`
- `showrunner`

## 6. Series State

The canonical series state should eventually track:

- series metadata and creative constraints
- characters and stable visual identities
- character goals and emotional states
- relationships
- character knowledge
- audience knowledge
- secrets and reveal status
- locations
- wardrobe
- props
- injuries and physical state
- timeline and chronology
- episode events
- unresolved questions
- promises/payoffs

## 7. Planned Execution Modes

### Fast
One generation, minimal review.

### Standard
Two independent candidates plus judge. This is the initial default.

### Quality
Three or more candidates, judge, merge/rewrite, critic, and additional validation.

## 8. Initial Scope

Phase 1 intentionally excludes final video production. The first objective is proving that Xerama can reliably generate a compelling and internally consistent text-level series before expensive media generation is introduced.
