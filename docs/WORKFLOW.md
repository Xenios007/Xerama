# Xerama Workflow

## Stage 0 — Creative Brief

The user supplies as much or as little as desired:

- premise or idea
- genre
- target audience
- language
- episode count
- episode duration
- tone/style
- production budget/constraints
- content restrictions

Missing creative fields may be proposed by Xerama but should remain editable.

## Stage 1 — Concept Competition

Standard mode:

1. Normalize creative brief.
2. Send identical requirements independently to Candidate Model A and Candidate Model B.
3. Validate both against the Concept Candidate schema.
4. Judge both candidates.
5. Decision: A, B, or MERGE.
6. If MERGE, send explicit merge instructions to a synthesis step.
7. Present/store the approved concept.

## Stage 2 — Series Foundation

From the approved concept:

1. Generate Series Bible.
2. Generate initial cast.
3. Generate relationship graph.
4. Define central secrets and information ownership.
5. Define world rules and production constraints.
6. Lock approved facts.

## Stage 3 — Season Architecture

Generate:

- macro arc
- major reversals
- reveal schedule
- relationship progression
- antagonist escalation
- false victories
- midpoint shift
- late-series crisis
- climax
- payoff

Then map those events to episode ranges.

## Stage 4 — Episode Planning

For each episode:

1. Load only relevant canon/state.
2. Generate beat-sheet candidates.
3. Score against story formula and recent episodes.
4. Select/rewrite.
5. Validate continuity.
6. Approve beat sheet.

## Stage 5 — Script

Convert approved beats into dialogue/action while respecting the duration budget.

Validation includes:

- episode objective remains intact
- dialogue does not expose future secrets
- characters only know established information
- cliffhanger is preserved
- no contradictions
- estimated duration is acceptable

## Stage 6 — Canon Commit

Approved episode events generate proposed state mutations.

```text
Episode
   ↓
Proposed State Changes
   ↓
Continuity Validator
   ↓
Approved Changes
   ↓
Canonical Series State
```

The next episode is generated from the updated state.

## Stage 7 — Directing

Approved script becomes:

```text
Episode
  ↓
Scenes
  ↓
Shots
  ↓
Reference Requirements
  ↓
Provider-Neutral Generation Instructions
```

## Stage 8 — Media Production

Future pipeline:

1. Resolve character/location/wardrobe references.
2. Generate or retrieve required reference assets.
3. Generate shots.
4. Generate/attach voice.
5. Lip sync where necessary.
6. Add music/SFX.
7. Add subtitles.
8. Assemble episode.

## Stage 9 — QC

Potential automated checks:

- identity consistency
- wardrobe continuity
- prop continuity
- location continuity
- lip/dialogue mismatch
- malformed frames
- shot duration
- subtitle accuracy
- audio clipping
- story continuity

Failed shots should be regenerated individually rather than regenerating an entire episode.

## Stage 10 — Analytics Feedback

After publication, performance can be associated with structured story features such as:

- hook type
- cliffhanger type
- episode duration
- dialogue/action ratio
- reveal type
- conflict type
- character pairing

Analytics should inform future recommendations while preserving explicit human creative control.
