# Xerama AI Model Strategy

## Objective

Xerama should not be tied to a single AI model or provider. Models are workers assigned to logical roles and selected through configuration.

## Initial Provider

The first LLM gateway is OpenRouter.

Development begins with free models where practical. Exact model IDs must remain configurable because free availability, limits, context windows, and quality can change.

## Standard Generation Mode

The initial default requires at least two independent candidate generations.

```text
Creative Brief
     │
 ┌───┴───┐
 ↓       ↓
Model A Model B
 ↓       ↓
 A       B
 └───┬───┘
     ↓
   Judge
     ↓
A / B / MERGE
```

Two candidates should normally be generated through separate inference calls. When possible, different model families should be used to increase creative diversity.

## Logical Model Roles

| Role | Responsibility |
| --- | --- |
| concept_generator_a | First independent concept |
| concept_generator_b | Second independent concept |
| judge | Compare, score, select, or merge |
| story_architect | Series and season structure |
| episode_writer | Dialogue and episode scripts |
| continuity_checker | Validate output against canonical state |
| retention_critic | Evaluate hooks, pacing, reveals, and cliffhangers |
| shot_planner | Convert scripts to structured production shots |
| showrunner | High-level approval/rewrite role for quality mode |

## Configuration Principle

Application code should request a role, not a hard-coded provider model.

Conceptually:

```python
result = await ai.generate(
    role="episode_writer",
    payload=episode_context,
)
```

The model gateway resolves the configured provider, model, parameters, fallbacks, timeout, and retry policy.

## Initial Modes

### Fast
- 1 candidate
- minimal validation
- intended for iteration and testing

### Standard
- 2 independent candidates
- 1 judge
- judge may select A, select B, or request merge
- initial Xerama default

### Quality
- 3+ candidates
- judge
- merge/rewrite
- critic
- continuity validation
- optional premium showrunner

## Temperature Guidance

Creative tasks may use higher sampling settings. Validation tasks should be deterministic where possible.

Examples:

- concept generation: creative/high
- dialogue: creative/moderate-high
- judge: moderate/low
- continuity: low
- structured extraction: low
- shot planning: low-moderate

Exact parameters should be benchmarked instead of permanently assumed.

## Structured Output

Where supported, Xerama should request structured JSON conforming to application schemas. Raw model responses, parsed responses, validation failures, retries, model IDs, latency, and token usage should eventually be logged for evaluation.

## Benchmarking

Model assignment should ultimately be determined by Xerama's own benchmark suite rather than reputation alone.

Benchmark categories should include:

- creative concept quality
- dialogue quality
- instruction following
- JSON/schema reliability
- long-context consistency
- continuity reasoning
- judging agreement
- latency
- token usage
- cost
- failure rate

## Cost Strategy

Use inexpensive/free workers for broad generation and reserve stronger paid models, when introduced, for high-value decisions such as final judging, difficult rewrites, or showrunner-level review.
