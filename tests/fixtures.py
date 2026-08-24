"""Shared scripted-JSON builders for pipeline/API tests.

Not a test module itself (no `test_` prefix) - imported by test_orchestrator.py
and test_api.py so both exercise identical fixture data.
"""


def concept(title: str) -> dict:
    return {
        "title": title,
        "genre": ["thriller"],
        "logline": f"logline for {title}",
        "premise": "premise",
        "protagonist": {"name": "Mara", "role": "protagonist", "desire": "the truth", "flaw": "pride"},
        "antagonistic_force": "her own family",
        "central_conflict": "loyalty vs. justice",
        "central_secret": "the sister faked her death",
        "emotional_engine": "betrayal",
        "opening_hook": "a funeral, and a text message from the dead",
        "serial_engine": "who else is lying",
        "major_reversals": ["the funeral was staged"],
        "ending_direction": "reconciliation or ruin",
        "production_notes": [],
    }


def judge_result(decision: str) -> dict:
    return {
        "decision": decision,
        "candidate_a": {"score": 7, "strengths": ["hook"], "weaknesses": []},
        "candidate_b": {"score": 8, "strengths": ["cast"], "weaknesses": []},
        "criteria": {
            "hook": 8,
            "emotional_intensity": 7,
            "conflict": 7,
            "originality": 6,
            "serial_potential": 8,
            "reversal_potential": 7,
            "cliffhanger_potential": 9,
            "production_feasibility": 8,
            "character_potential": 7,
        },
        "reason": "Candidate A has a stronger hook.",
        "merge_instructions": {"take_from_a": [], "take_from_b": [], "requirements": []},
    }


def bible() -> dict:
    return {
        "title": "Blood Sisters",
        "logline": "logline",
        "genres": ["thriller"],
        "tone": ["tense"],
        "target_audience": "general",
        "episode_count": 3,
        "episode_duration_seconds": 75,
        "premise": "premise",
        "themes": ["betrayal"],
        "emotional_engine": "betrayal",
        "central_dramatic_question": "who is lying?",
        "protagonist_objective": "find her sister",
        "primary_opposition": "her own family",
        "world_rules": [],
        "central_secret": "the sister faked her death",
        "ending_target": "reconciliation",
        "prohibited_contradictions": [],
        "locked_facts": ["Mara has a twin sister named Lena"],
    }


def cast() -> dict:
    return {
        "characters": [
            {
                "id": "CHAR_001",
                "name": "Mara",
                "role": "protagonist",
                "age": "32",
                "description": "sharp, guarded",
                "personality": "controlled",
                "goal": "find her sister",
                "fear": "being replaced",
                "flaw": "pride",
                "secret": "she knew all along",
                "character_dna": {},
                "status": "active",
            },
            {
                "id": "CHAR_002",
                "name": "Lena",
                "role": "antagonist",
                "age": "32",
                "description": "Mara's twin",
                "personality": "charming",
                "goal": "disappear for good",
                "fear": "being found",
                "flaw": "vanity",
                "secret": "faked her own death",
                "character_dna": {},
                "status": "active",
            },
        ],
        "relationships": [
            {
                "source_character_id": "CHAR_001",
                "target_character_id": "CHAR_002",
                "relationship_type": "twin sisters",
                "trust_level": 0.2,
                "valid_from_episode": 1,
            }
        ],
    }


def outline(n: int) -> dict:
    return {
        "episode_number": n,
        "title": f"Episode {n}",
        "objective": "find the truth",
        "opening_hook": "a scream echoes through the empty apartment",
        "stakes": "her freedom",
        "conflict": "sister vs. sister",
        "escalation": ["she finds the letter"],
        "turn": "the letter was a forgery",
        "reveal": "he was never who he claimed",
        "audience_information_gain": [],
        "character_information_gain": [],
        "cliffhanger": {"type": "identity_reveal", "event": "the mask comes off"},
        "canon_changes": [],
        "duration_target_seconds": 75,
    }


def outline_set(episode_count: int) -> dict:
    return {"outlines": [outline(n) for n in range(1, episode_count + 1)]}


def script() -> dict:
    return {
        "episode_number": 1,
        "title": "Episode 1",
        "scenes": [
            {
                "scene_number": 1,
                "location": "apartment",
                "time_of_day": "night",
                "characters": ["CHAR_001"],
                "action": "Mara reads the letter with shaking hands.",
                "dialogue": [
                    {"character_id": "CHAR_001", "character_name": "Mara", "line": "This can't be real."}
                ],
            }
        ],
        "estimated_duration_seconds": 75,
    }


def shot_plan() -> dict:
    return {
        "episode_number": 1,
        "scenes": [
            {
                "scene_number": 1,
                "location": "apartment",
                "time_of_day": "night",
                "characters": ["CHAR_001"],
                "objective": "reveal the forgery",
                "conflict": "denial vs. evidence",
                "outcome": "she believes it",
                "shots": [
                    {
                        "shot_number": 1,
                        "scene_number": 1,
                        "narrative_function": "hook",
                        "character_ids": ["CHAR_001"],
                        "dialogue": "This can't be real.",
                        "action": "Mara opens the letter",
                        "duration_seconds": 5,
                        "camera": {
                            "shot_size": "close-up",
                            "angle": "eye-level",
                            "lens": "50mm",
                            "movement": "static",
                        },
                        "visual": {"composition": "centered", "lighting": "low-key", "emotion": "dread"},
                        "references": {},
                        "micro_beats": [],
                        "audio_mode": "native",
                        "continuity_requirements": [],
                        "generation_status": "planned",
                    }
                ],
            }
        ],
    }
