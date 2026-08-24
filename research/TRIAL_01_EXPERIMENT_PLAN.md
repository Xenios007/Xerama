# Trial 01 — Free-First AI Microdrama Experiment

## Purpose

Trial 01 is not intended to produce a commercially perfect season. It is intended to discover the minimum reliable Xerama workflow using available free tiers, trial credits, and low-cost models before committing to paid subscriptions.

## Success definition

Produce a coherent **3-episode vertical microdrama pilot** with:

- 2–3 recurring characters
- 1–3 recurring locations
- stable visual identity
- stable voice identity
- understandable dialogue
- cliffhanger endings
- native or final 9:16 delivery
- recorded generation metrics for every stage

Target episode length: approximately 45–90 seconds for the first experiment.

## Stage A — Story benchmark

Use OpenRouter.

For the same creative brief:

- Model A → Concept A
- Model B → Concept B
- Judge → A/B/MERGE

Then generate:

- series bible
- 3-episode mini arc
- episode beat sheets
- scripts
- continuity state

### Record

- model ID
- free/paid status
- prompt version
- latency
- token usage if available
- JSON validity
- human story score
- judge score
- retries

## Stage B — Character image benchmark

For each candidate image model/provider available to us:

Generate the same character pack.

Score:

- identity consistency
- face quality
- full-body consistency
- expression consistency
- wardrobe consistency
- editability/reference support
- generation time
- cost/credits

Pick one provider for Trial 01, not necessarily the theoretically best provider.

## Stage C — Storyboard benchmark

Generate approved keyframes for Episode 1 before any video.

Measure:

- how often the correct characters appear
- correct wardrobe
- correct location
- correct framing
- prompt iterations needed

## Stage D — Video benchmark

Select a small set of representative shots:

1. close-up reaction
2. single-character dialogue
3. two-character confrontation
4. walking/motion
5. prop interaction
6. establishing shot

Test available free/trial video models against the same shot specification where their interfaces allow it.

Score:

- identity
- motion
- acting/emotion
- lip sync/audio if applicable
- anatomy
- prompt adherence
- usable first-pass rate
- latency
- credits/cost per usable second

## Stage E — Voice/lip-sync benchmark

If native video audio is not sufficient:

- assign persistent voices
- generate identical lines through available TTS options
- test lip-sync options on the same face shot

Score naturalness, identity stability, emotion, timing, multilingual potential, and cost.

## Stage F — Full 3-episode run

Once individual stages are chosen:

```text
3 scripts
→ shot lists
→ storyboard frames
→ video generations
→ retakes
→ voice/lip sync
→ edit
→ subtitles
→ QC
→ 3 final episodes
```

## Metrics database

Every generation should eventually produce a record similar to:

```json
{
  "project": "trial-01",
  "episode": 1,
  "shot": 7,
  "stage": "video",
  "provider": "provider-name",
  "model": "model-name",
  "prompt_version": "v1",
  "duration_requested": 5,
  "latency_seconds": 0,
  "cost_usd": 0,
  "credits": 0,
  "accepted": false,
  "reject_reasons": ["face_drift", "bad_hand"],
  "attempt": 1
}
```

## Decisions after Trial 01

For every stage answer:

- Is free good enough?
- If not, what specifically failed?
- Which paid model is most likely to fix that failure?
- What is the expected added cost per finished episode?
- Is the improvement visible enough to justify paying?

Only then subscribe/buy credits.

## Scaling gate

Do not attempt a 30–100 episode production until Trial 01 demonstrates:

- reproducible character identity
- manageable retake rate
- predictable cost
- reliable asset storage
- reproducible prompt/state pipeline
- acceptable editing workload

After success, Trial 02 should expand to roughly 10 episodes before a full season.
