# Research Papers and Benchmarks

_Last researched: 2026-08-24_

## Why this matters

Commercial AI microdrama workflows and academic research are converging on the same failure points: weak pacing, identity drift, spatial inconsistency, visual/narrative mismatch, and cascading errors from loosely coupled one-shot generation.

Xerama should borrow the evaluation ideas before we write our own generation engine.

## One Sentence, One Drama (2026)

Paper:
- https://arxiv.org/abs/2605.22144

The paper identifies three major shortcomings in common short-drama pipelines:

1. weak narrative pacing — hooks/escalation/endings fail;
2. spatial inconsistency — scene layouts and character positions drift;
3. production QC burden — manual review is needed across script and visuals.

Its proposed solution uses:

- hierarchical multi-agent generation;
- debate/refinement for story quality;
- 3D-grounded first frames for spatial consistency;
- multi-stage reviewer loops;
- targeted revisions rather than blind full regeneration;
- scene-level BGM matching;
- scene-transition planning.

It introduces **Short-Drama-Bench**, which is directly relevant to Xerama's future evaluation suite.

### Xerama takeaway

Our current Candidate A + Candidate B + Judge concept is directionally correct, but it should expand into reviewer loops at multiple stages:

```text
Story Reviewer
Storyboard Reviewer
Identity Reviewer
Video Reviewer
Continuity Reviewer
```

A failure should route back to the smallest responsible stage.

## DramaDirector (2026)

Paper:
- https://arxiv.org/abs/2606.24107

Code:
- https://github.com/iLearn-Lab/DramaDirector

DramaDirector argues that text-only prompt planning is insufficient for short dramas because rapid shot rhythms and dialogue-driven focus changes require cinematographic grounding.

Its important contribution is separating:

- static visual conditions;
- dynamic narrative conditions;
- shot geometry;
- first-frame generation;
- image-to-video synthesis.

The associated **DramaBoard** benchmark is built from 35 live-action dramas, about 2,800 episodes, and about 81,000 shots according to the paper.

### Xerama takeaway

Our Shot schema should not stop at `camera=close-up`. It should include explicit spatial information:

```text
shot scale
camera angle
camera motion
subject position
screen direction
eye line
pose/action
expression
background geometry
duration
```

Later we can retrieve cinematographic patterns from a library of real/legal reference shots instead of asking the LLM to invent every composition.

## Co-Director (2026)

Paper:
- https://arxiv.org/abs/2604.24842

Co-Director frames agentic video storytelling as a global optimization problem. It notes that independent chained modules suffer semantic drift and cascading failures.

Its architecture combines global creative search with local multimodal self-refinement.

### Xerama takeaway

Generation should preserve a **global creative configuration** (series style, character identities, story objectives) while allowing local shot repair. Do not let a local retry silently mutate global canon.

## Agentic Video Generation / Executable Event Graphs (2026)

Paper:
- https://arxiv.org/abs/2604.10383

This work is not specifically a microdrama generator, but it reinforces an important architectural lesson: unconstrained staged LLM output can fail to produce executable production specifications. The paper separates narrative reasoning from a programmatic state backend that enforces constraints.

### Xerama takeaway

The LLM should propose; code should validate and commit.

This supports Xerama's existing canon rule:

```text
LLM proposal
→ schema validation
→ programmatic constraints
→ continuity validation
→ approval
→ canonical state
```

## Proposed Xerama benchmark layers

### Story benchmark

- hook strength
- goal clarity
- conflict
- escalation
- information gap
- reversal
- cliffhanger
- payoff progress
- dialogue economy
- repetition

### Continuity benchmark

- identity consistency
- character knowledge consistency
- relationship state
- timeline
- props
- wardrobe
- injury/physical state
- location

### Storyboard benchmark

- plot/shot alignment
- shot diversity
- screen direction
- eye lines
- character positioning
- location consistency
- shot duration suitability

### Visual benchmark

- face similarity to canonical reference
- costume similarity
- environment similarity
- anatomy/artifact failures
- composition
- style/grade consistency

### Video benchmark

- motion quality
- temporal identity stability
- dialogue/lip alignment
- camera adherence
- physical plausibility
- first/last-frame adherence
- transition quality

### Production benchmark

- generations per accepted shot
- failure rate
- retry count
- wall-clock time
- tokens
- credits/cost
- human intervention minutes

## Research decision

Trial 01 should log these metrics even if many are initially human-scored. We can automate them later. Without a benchmark, changing models will only give us subjective impressions and we will not know whether paid models are actually worth the upgrade.
