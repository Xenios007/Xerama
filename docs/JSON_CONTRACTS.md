# Xerama AI JSON Contracts

## Purpose

AI stages should exchange structured, validated objects whenever practical. These examples define the initial contracts to implement during XER-001 through XER-010.

## Concept Candidate

```json
{
  "title": "string",
  "genre": ["string"],
  "logline": "string",
  "premise": "string",
  "protagonist": {
    "name": "string",
    "role": "string",
    "desire": "string",
    "flaw": "string"
  },
  "antagonistic_force": "string",
  "central_conflict": "string",
  "central_secret": "string",
  "emotional_engine": "string",
  "opening_hook": "string",
  "serial_engine": "string",
  "major_reversals": ["string"],
  "ending_direction": "string",
  "production_notes": ["string"]
}
```

## Judge Result

```json
{
  "decision": "A | B | MERGE",
  "candidate_a": {
    "score": 0,
    "strengths": ["string"],
    "weaknesses": ["string"]
  },
  "candidate_b": {
    "score": 0,
    "strengths": ["string"],
    "weaknesses": ["string"]
  },
  "criteria": {
    "hook": 0,
    "emotional_intensity": 0,
    "conflict": 0,
    "originality": 0,
    "serial_potential": 0,
    "reversal_potential": 0,
    "cliffhanger_potential": 0,
    "production_feasibility": 0
  },
  "reason": "string",
  "merge_instructions": {
    "take_from_a": ["string"],
    "take_from_b": ["string"],
    "requirements": ["string"]
  }
}
```

`merge_instructions` may be empty when the decision is A or B.

## Series Bible

```json
{
  "title": "string",
  "logline": "string",
  "genres": ["string"],
  "tone": ["string"],
  "target_audience": "string",
  "episode_count": 30,
  "episode_duration_seconds": 75,
  "themes": ["string"],
  "emotional_engine": "string",
  "central_dramatic_question": "string",
  "world_rules": ["string"],
  "central_secret": "string",
  "ending_target": "string",
  "locked_facts": ["string"]
}
```

## Episode Beat Sheet

```json
{
  "episode_number": 1,
  "objective": "string",
  "opening_hook": "string",
  "stakes": "string",
  "conflict": "string",
  "escalation": ["string"],
  "turn": "string",
  "reveal": "string",
  "audience_information_gain": ["string"],
  "character_information_gain": [
    {
      "character_id": "string",
      "fact_id": "string"
    }
  ],
  "cliffhanger": {
    "type": "string",
    "event": "string"
  },
  "canon_changes": ["string"],
  "duration_target_seconds": 75
}
```

## Quality Score

All individual dimensions use a 0–10 scale.

```json
{
  "hook": 0.0,
  "conflict": 0.0,
  "emotional_intensity": 0.0,
  "information_gap": 0.0,
  "reversal": 0.0,
  "cliffhanger": 0.0,
  "character_consistency": 0.0,
  "continuity": 0.0,
  "serial_progress": 0.0,
  "originality": 0.0,
  "production_feasibility": 0.0,
  "repetition_risk": 0.0,
  "overall": 0.0,
  "blocking_issues": ["string"],
  "recommendations": ["string"]
}
```

## Shot

```json
{
  "shot_number": 1,
  "duration_seconds": 5.0,
  "character_ids": ["CHAR_001"],
  "location_id": "LOC_001",
  "wardrobe_ids": ["WARD_001"],
  "action": "string",
  "emotion": "string",
  "camera_framing": "string",
  "camera_motion": "string",
  "lighting": "string",
  "dialogue": "string",
  "continuity_requirements": ["string"]
}
```

## Contract Rules

1. IDs referenced by generated objects must exist or be explicitly proposed as new entities.
2. Enum-like values should become formal enums in application schemas.
3. Scores must be bounded and validated.
4. Unknown information should be represented explicitly rather than fabricated.
5. Parsing failure should trigger repair/retry rather than silently accepting malformed output.
6. Raw model output should be retained for debugging and benchmarks.
7. Schema version should eventually accompany persisted AI artifacts.
