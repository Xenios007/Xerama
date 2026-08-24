# Character & Visual Continuity Playbook

_Last researched: 2026-08-24_

## Why this matters

Public production guides overwhelmingly identify character drift as one of the biggest failure modes in AI series production. Text descriptions alone are insufficient because each generation can reinterpret unspecified facial, hair, clothing, and body details.

The production pattern is to separate **character creation** from **character animation**.

## Identity hierarchy

```text
CHARACTER
├── Root Identity
│   └── permanent face/body identity
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
└── Voice Identity
```

Never generate a recurring character from scratch once the identity is approved.

## Root identity

Create one high-quality root portrait per principal character and treat it as immutable unless the character is deliberately recast.

Record explicit visual constraints:

- approximate age
- face shape
- skin tone
- eye color/shape
- hairstyle/color/length
- body type/height relationship
- signature details
- forbidden changes

## Reference pack

Current creator/studio guidance ranges from a handful of key images to larger packs. One detailed Seedance workflow reports 12–15 locked references per lead including multiple angles, expressions, full-body poses, and details.

For Xerama trial production, start lean:

- front portrait
- 3/4 portrait
- side portrait
- full body
- neutral expression
- angry expression
- happy/soft expression
- one signature detail close-up if needed

Add references only when testing shows they improve consistency; excessive references can complicate routing and some providers cap reference count.

## Wardrobe as assets

Do not prompt "same clothes as before." Create versioned wardrobe assets.

Example:

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

A room should have stable layout, furniture, palette, and hero props.

## Prop continuity

Props with story importance need identity/version tracking:

- wedding ring
- phone
- necklace
- document
- weapon/tool where appropriate to story
- vehicle
- photograph

Track owner/location/state per episode.

## Reference-frame workflow

Preferred trial workflow:

```text
Approved Character Pack
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

## Continuity scoring

Every generated shot can eventually be scored on:

- face similarity
- hair similarity
- body/age consistency
- wardrobe correctness
- location correctness
- prop correctness
- time-of-day/look correctness
- identity confusion when multiple characters appear

V1 may rely on human approval; later versions can use multimodal models/embeddings/face comparison where legally and technically appropriate.

## Drift response

If a shot drifts:

1. Do not modify the canonical character description to match the bad output.
2. Reject the shot.
3. Reuse the approved references.
4. Simplify the action/camera if needed.
5. Generate a stronger still reference first.
6. Retry video from the approved frame.
7. Route to another provider if repeated failures occur.

## Production design recommendation for first trial

Make the first Xerama drama intentionally easy:

- 2–3 main characters
- contemporary clothing
- 1–3 recurring locations
- minimal crowd scenes
- minimal complex hand/prop interaction
- limited costume changes
- no large battle/action sequences

The purpose of Trial 1 is to prove repeatability, not demonstrate every possible model capability.

## Sources

- https://ogunstudios.com/blog/ai-character-consistency-micro-drama
- https://ogunstudios.com/blog/how-to-make-ai-short-drama
- https://seedancereview.com/blog/seedance-ai-short-drama-workflow/
- https://www.axisaistudios.com/blog/ai-production-tools-that-are-changing-vertical-drama-workflows-in-2026
- Creator discussion on repeated reference images: https://www.reddit.com/r/aivideos/comments/1smtzb9/seedance_20_character_consistency_across_shots/
