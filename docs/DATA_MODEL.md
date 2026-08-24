# Xerama Canonical Data Model

## Purpose

Xerama needs a durable source of truth that is independent of any LLM context window. Models may propose state changes, but only validated state becomes canon.

## Entity Hierarchy

```text
Project
└── Series
    ├── Series Bible
    ├── Characters
    │   ├── Relationships
    │   ├── Knowledge
    │   ├── Secrets
    │   ├── Visual Identity
    │   └── State History
    ├── Locations
    ├── Props
    ├── Story Arcs
    ├── Reveals
    └── Episodes
        ├── Beat Sheet
        ├── Script
        ├── Scenes
        │   └── Shots
        ├── State Changes
        └── Quality Reports
```

## Project

Represents a Xerama production workspace.

Suggested fields:

- `id`
- `name`
- `description`
- `status`
- `default_language`
- `target_platform`
- `created_at`
- `updated_at`

## Series

Suggested fields:

- `id`
- `project_id`
- `title`
- `logline`
- `genre`
- `subgenres`
- `tone`
- `target_audience`
- `episode_count_target`
- `episode_duration_target_seconds`
- `aspect_ratio`
- `status`

## Series Bible

Stores approved creative truth:

- premise
- central dramatic question
- emotional engine
- themes
- world rules
- protagonist objective
- primary opposition
- central secret
- ending target
- prohibited contradictions
- locked facts

## Character

Suggested fields:

- `id`
- `series_id`
- `name`
- `role`
- `age`
- `description`
- `personality`
- `goal`
- `fear`
- `flaw`
- `secret`
- `visual_identity_id`
- `voice_identity_id`
- `status`

## Relationship

Relationship state must be versionable because it changes over time.

Suggested fields:

- `source_character_id`
- `target_character_id`
- `relationship_type`
- `public_status`
- `private_status`
- `trust_level`
- `romantic_state`
- `valid_from_episode`
- `valid_to_episode`

## Knowledge State

A fact should not simply be marked revealed. Xerama needs to know who knows it.

```text
Fact
├── Audience: knows / suspects / unknown
├── Character A: knows / suspects / believes_false / unknown
├── Character B: knows / suspects / believes_false / unknown
└── Reveal schedule
```

Suggested fact fields:

- `id`
- `series_id`
- `statement`
- `truth_status`
- `importance`
- `introduced_episode`
- `planned_reveal_episode`
- `actual_reveal_episode`

## Story Arc

Suggested fields:

- `id`
- `series_id`
- `name`
- `type`
- `start_episode`
- `target_end_episode`
- `objective`
- `setup`
- `escalation`
- `payoff`
- `status`

## Episode

Suggested fields:

- `id`
- `series_id`
- `episode_number`
- `title`
- `objective`
- `opening_hook`
- `central_conflict`
- `turn`
- `reveal`
- `cliffhanger_type`
- `cliffhanger`
- `duration_target_seconds`
- `status`

## Episode State Change

Every approved episode should explicitly declare changes to canon.

Examples:

- character learns fact
- relationship changes
- secret exposed
- injury added/removed
- character moves location
- prop changes ownership
- promise created
- promise paid off

State changes are validated before commit.

## Scene

Suggested fields:

- `id`
- `episode_id`
- `scene_number`
- `location_id`
- `time_of_day`
- `characters`
- `objective`
- `conflict`
- `outcome`

## Shot

Suggested fields:

- `id`
- `scene_id`
- `shot_number`
- `duration_seconds`
- `character_ids`
- `location_id`
- `wardrobe_ids`
- `action`
- `emotion`
- `camera_framing`
- `camera_motion`
- `lighting`
- `dialogue`
- `continuity_requirements`
- `generation_status`

## Quality Report

Store scores rather than discarding them after generation.

Initial dimensions:

- hook
- premise clarity
- conflict
- emotional intensity
- information gap
- reversal
- cliffhanger
- character quality
- serial potential
- originality
- continuity
- repetition
- production feasibility
- overall score

## Canon Commit Rule

```text
Model Proposal
      ↓
Schema Validation
      ↓
Continuity Validation
      ↓
Quality / Rule Validation
      ↓
Optional Human Approval
      ↓
Commit to Canon
```

This boundary is fundamental: generated text is not automatically series truth.
