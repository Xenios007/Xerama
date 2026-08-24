# Free-First Model Strategy

_Last researched: 2026-08-24_

## Objective

Do not pay for premium inference until Xerama has enough instrumentation to identify exactly where free models fail.

Free models are not the final production commitment. They are the cheapest way to validate architecture, prompts, schemas, state management, retries, and the story pipeline.

## OpenRouter free layer

OpenRouter currently provides `openrouter/free`, which routes requests among available free models and filters the pool based on requested capabilities such as image understanding, tool calling, and structured outputs.

Sources:
- https://openrouter.ai/docs/guides/routing/routers/free-router
- https://openrouter.ai/openrouter/free/
- https://openrouter.ai/collections/free-models

At the time of research the free pool includes models from several families and changes over time. Therefore **Xerama must discover/configure model IDs rather than hard-code today's list**.

## Important caveat

`openrouter/free` may select models dynamically. That is useful for zero-cost experimentation but bad for controlled benchmarking.

Xerama therefore needs two modes:

### FREE_RANDOM
Use `openrouter/free` to maximize zero-cost availability.

### FREE_PINNED
Use explicit `:free` model IDs for reproducible A/B tests.

OpenRouter documents the `:free` variant for selecting specific free versions.

Source:
- https://openrouter.ai/docs/guides/routing/model-variants/free

## Structured outputs

OpenRouter supports JSON-schema structured outputs on compatible models. Xerama should request strict schemas for concepts, judges, bibles, beats, shots, and state changes.

Source:
- https://openrouter.ai/docs/guides/features/structured-outputs

The model catalog exposes supported parameters, so Xerama can eventually filter models for required capabilities before assignment.

Source:
- https://openrouter.ai/docs/guides/overview/models

## V1 LLM experiment matrix

For each logical task, test at least two free model families when available:

| Task | Candidate A | Candidate B | Judge |
| --- | --- | --- | --- |
| Concept | pinned free model | different pinned free model | free reasoning model |
| Series architecture | free reasoning model | second free model | judge |
| Episode beats | free model A | free model B | judge |
| Script | free creative model A | free creative model B | judge/critic |
| Continuity | deterministic free model | fallback | programmatic checks + model |
| Shot planning | structured-output free model | fallback | schema/programmatic checks |

Do not permanently assign a model until benchmark data exists.

## Model promotion policy

A paid model should be introduced only when a free stage repeatedly fails one of these gates:

- schema success rate
- story quality
- long-context/canon accuracy
- continuity
- dialogue quality
- judge reliability
- latency/reliability

Then test a paid model on the **same benchmark inputs**.

Upgrade only if quality/cost improvement is measurable.

## Suggested hybrid economics later

Likely production architecture:

```text
FREE/CHEAP WORKERS
  generate candidates
  extract state
  produce routine shot metadata
          ↓
STRONGER JUDGE / SHOWRUNNER
  select
  repair
  approve
          ↓
EXPENSIVE MEDIA MODELS
  only after story/shot approval
```

The expensive model should not be asked to do work a cheaper model already does reliably.

## Privacy note

Free inference may have different provider data policies than paid/private endpoints. Xerama should record provider/model and later support provider privacy requirements. Do not place private actor scans, contracts, unreleased commercial scripts, or sensitive credentials into arbitrary free endpoints without reviewing provider terms.

## Trial 01 success condition

We do not need a perfect model. We need a free configuration capable of producing:

1. valid structured concepts;
2. two genuinely different candidates;
3. usable judge decisions;
4. one coherent 3-episode mini-arc;
5. consistent character/world state;
6. structured shots ready for image/video experimentation.

If that works, the architecture is ready for the first media tests.
