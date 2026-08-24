"""Deterministic SFX-cue derivation from shot/micro-beat events (MODULE-038).

Pure keyword-based heuristic, no LLM call - "derive optional SFX cues from
shot/micro-beat events" while "avoiding overfilling scenes with unnecessary
effects" via a curated keyword list and a hard per-shot cap. Micro-beats
that mention a trigger word are preferred (they carry real timing); a match
in the shot's free-text `action` falls back to a short default window at
the start of the shot.
"""

from xerama.domain.scene import Shot

MAX_SFX_CANDIDATES_PER_SHOT = 2

# Curated, not exhaustive - a fuller catalog can be layered on if this
# proves too sparse for real production scripts.
_SFX_KEYWORDS: dict[str, str] = {
    "door": "door slams",
    "glass": "glass breaks",
    "gunshot": "gunshot",
    "gun": "gunshot",
    "phone": "phone rings",
    "footstep": "footsteps",
    "car": "car engine/tires",
    "knock": "knocking",
    "thunder": "thunder",
    "rain": "rain ambience",
    "siren": "siren",
    "scream": "scream",
    "slap": "slap impact",
    "crash": "crash impact",
}


def derive_sfx_candidates(shot: Shot) -> list[tuple[str, float, float]]:
    """Returns up to `MAX_SFX_CANDIDATES_PER_SHOT` (description, start_seconds,
    end_seconds) tuples - the caller persists these as draft `SoundEffectCue`
    rows if it wants them."""
    candidates: list[tuple[str, float, float]] = []
    seen: set[str] = set()

    for beat in shot.micro_beats:
        lowered = beat.description.lower()
        for keyword, description in _SFX_KEYWORDS.items():
            if keyword in lowered and description not in seen:
                seen.add(description)
                candidates.append((description, beat.start_seconds, beat.end_seconds))
                if len(candidates) >= MAX_SFX_CANDIDATES_PER_SHOT:
                    return candidates

    lowered_action = shot.action.lower()
    for keyword, description in _SFX_KEYWORDS.items():
        if keyword in lowered_action and description not in seen:
            seen.add(description)
            candidates.append((description, 0.0, min(1.0, shot.duration_seconds)))
            if len(candidates) >= MAX_SFX_CANDIDATES_PER_SHOT:
                return candidates

    return candidates
