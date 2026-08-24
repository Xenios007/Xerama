# Character & Visual Continuity Playbook

_Last researched: 2026-08-24_

## Why this matters

Public production guides and source-level study of Wind Comic identify character drift as one of the biggest failure modes in AI series production. Text descriptions alone are insufficient because each generation can reinterpret unspecified facial, hair, clothing and body details.

The production pattern is to separate **character creation** from **character animation**, then enforce identity through references, textual DNA, centralized consistency policy and QC/retry loops.

## Identity hierarchy

```text
CHARACTER
├── Root Identity
│   └── permanent face/body identity
├── Character DNA
│   └── compact stable visual signature
├── Reference Pack
│   ├── front
│   ├── 3/4
│   ├── side
│   ├── full body
│   └── expressions
├── Wardrobe State
│   ├── WARD-001
│   ├── WARD-002
│   └── ...
├── Physical State
│   ├── normal
│   ├── injured
│   ├── wet
│   └── aged/time-jump
├── Voice Identity
└── Provenance / Consent
```

Never generate a recurring character from scratch once the identity is approved.

## Root identity

Create one high-quality root portrait per principal character and treat it as immutable unless the character is deliberately recast.

Record explicit visual constraints:

- approximate age;
- face shape;
- skin tone;
- eye color/shape;
- hairstyle/color/length;
- body type/height relationship;
- signature details;
- forbidden changes.

## Character DNA

Wind Comic demonstrates a useful second identity channel: derive a compact textual visual signature from the approved root reference and inject it into downstream prompts alongside the image reference.

Useful DNA dimensions include:

- eyes;
- jaw/face structure;
- nose;
- mouth;
- hairstyle;
- hair color;
- skin tone;
- signature outfit/detail.

Xerama should store Character DNA as structured canonical data. It is not a replacement for reference images; it reinforces them and provides a provider-independent identity description.

## Reference pack

Current creator/studio guidance ranges from a handful of key images to larger packs. One detailed Seedance workflow reports 12–15 locked references per lead including multiple angles, expressions, full-body poses and details.

For Xerama trial production, start lean:

- front portrait;
- 3/4 portrait;
- side portrait;
- full body;
- neutral expression;
- angry expression;
- happy/soft expression;
- one signature detail close-up if needed.

Add references only when testing shows they improve consistency; excessive references can complicate routing and providers cap reference count.

## Central consistency policy

Reference selection should not be scattered across prompts. Xerama should have one policy/service that decides, per shot:

- which character roots to include;
- which view/reference best matches the shot;
- Character DNA to inject;
- wardrobe/state reference;
- Style Bible reference;
- provider-specific reference count/strength;
- continuity frame from the previous shot when relevant.

This is a major lesson from Wind Comic's architecture.

## Wardrobe as assets

Do not prompt "same clothes as before." Create versioned wardrobe assets.

```text
CHAR-001 Elena
  WARD-001 office_black_dress
  WARD-002 hospital_gown
  WARD-003 red_evening_dress
```

Episode/scene state points to an asset ID.

## Location continuity

Treat recurring locations similarly:

```text
LOC-001 apartment_living_room
  VIEW-001 doorway_to_sofa
  VIEW-002 sofa_to_kitchen
  VIEW-003 window_wall
  NIGHT-LOOK
  DAY-LOOK
```

A room should have stable layout, furniture, palette and hero props.

## Prop continuity

Props with story importance need identity/version tracking:

- wedding ring;
- phone;
- necklace;
- document;
- vehicle;
- photograph;
- other plot-critical object.

Track owner/location/state per episode.

## Style Bible

Wind Comic validates generating a canonical Style Bible frame before bulk generation. Xerama should approve a production-level visual anchor containing:

- palette;
- lighting style;
- color temperature;
- texture/render style;
- contrast/exposure character;
- aspect/composition conventions.

Generated shots should be compared against the Style Bible for drift.

## Reference-frame workflow

Preferred trial workflow:

```text
Approved Character Pack + DNA
        +
Approved Style Bible
        +
Approved Location Pack
        +
Wardrobe Asset
        +
Shot Description
        ↓
Storyboard / Keyframe
        ↓
Human/AI QC
        ↓
Approved Reference Frame
        ↓
Image-to-Video
```

This lets us solve composition and identity before spending video credits.

## Actual last-frame continuity

For continuous adjacent shots, the real final frame of Shot N can be a better continuity reference for Shot N+1 than the original storyboard because it captures the actual generated pose, expression and lighting.

```text
Shot N video
 -> extract final frame
 -> add character/style anchors
 -> generate Shot N+1
```

This should be optional because it reduces parallelism. Independent shots can still generate concurrently.

## Continuity scoring

Every generated shot can eventually be scored on:

- face similarity;
- hair similarity;
- body/age consistency;
- wardrobe correctness;
- location correctness;
- prop correctness;
- time-of-day/look correctness;
- style similarity;
- identity confusion when multiple characters appear.

Multi-character shots should score important characters separately. A correct protagonist should not compensate for a completely wrong supporting character.

## Automated identity retry

Wind Comic demonstrates a practical retry pattern:

```text
Generate
 -> identity vision score
 -> pass: accept
 -> fail: strengthen reference conditioning
 -> regenerate
 -> repeated fail: alternate provider or human review
```

Xerama should record each attempt and rejection reason instead of overwriting failed takes.

## Drift response

If a shot drifts:

1. Do not modify canonical character data to match the bad output.
2. Reject/version the shot.
3. Reuse approved root references and Character DNA.
4. Increase or improve reference conditioning if supported.
5. Simplify action/camera if needed.
6. Generate a stronger still reference first.
7. Retry video from the approved frame.
8. Route to another provider if repeated failures occur.
9. Escalate to human review only after automated repair options are exhausted or budget policy blocks more attempts.

## Production design recommendation for first trial

Make the first Xerama drama intentionally easy:

- 2–3 main characters;
- contemporary clothing;
- 1–3 recurring locations;
- minimal crowd scenes;
- minimal complex hand/prop interaction;
- limited costume changes;
- no large battle/action sequences.

The purpose of Trial 01 is to prove repeatability, not demonstrate every possible model capability.

## Implementation requirements derived from Wind Comic

Trial 01 data structures should include:

- immutable character root asset ID;
- Character DNA object;
- reference-pack asset IDs;
- voice ID/profile;
- wardrobe/state IDs;
- Style Bible asset ID;
- per-shot selected references;
- identity/style QC scores;
- retry/take lineage;
- provenance/consent metadata.

## Sources

- Wind Comic source-level analysis: `research/WIND_COMIC_DEEP_DIVE.md`
- https://github.com/ChrisChen667788/wind-comic
- https://ogunstudios.com/blog/ai-character-consistency-micro-drama
- https://ogunstudios.com/blog/how-to-make-ai-short-drama
- https://seedancereview.com/blog/seedance-ai-short-drama-workflow/
- https://www.axisaistudios.com/blog/ai-production-tools-that-are-changing-vertical-drama-workflows-in-2026
- Creator discussion on repeated reference images: https://www.reddit.com/r/aivideos/comments/1smtzb9/seedance_20_character_consistency_across_shots/
