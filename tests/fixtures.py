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


def season_plan() -> dict:
    """A valid 3-episode season plan matching `cast()`'s CHAR_001/CHAR_002 -
    passes SeasonValidator cleanly (one deliberately open mystery, upward
    escalation, non-repeating cliffhangers, full character-arc coverage)."""
    return {
        "series_title": "Blood Sisters",
        "episode_count": 3,
        "acts": [
            {
                "act_number": 1,
                "name": "Setup",
                "start_episode": 1,
                "end_episode": 1,
                "objective": "Introduce the mystery",
            },
            {
                "act_number": 2,
                "name": "Escalation",
                "start_episode": 2,
                "end_episode": 2,
                "objective": "Deepen the conflict",
            },
            {
                "act_number": 3,
                "name": "Turn",
                "start_episode": 3,
                "end_episode": 3,
                "objective": "First major reversal",
            },
        ],
        "mysteries": [
            {
                "id": "MYS_001",
                "question": "Is Lena really dead?",
                "introduced_episode": 1,
                "resolution_episode": 3,
                "status": "resolved",
            },
            {
                "id": "MYS_002",
                "question": "Who else knew about the plan?",
                "introduced_episode": 2,
                "resolution_episode": None,
                "status": "open",
            },
        ],
        "promises": [
            {
                "id": "PROM_001",
                "description": "Mara promises to find the truth no matter what",
                "setup_episode": 1,
                "payoff_episode": 3,
                "status": "resolved",
            }
        ],
        "reveals": [
            {
                "id": "REV_001",
                "description": "Mara finds Lena's forged letter",
                "planned_episode": 1,
                "mystery_id": "MYS_001",
                "depends_on": [],
                "audience_knowledge_before": "unknown",
                "audience_knowledge_after": "suspects",
            },
            {
                "id": "REV_002",
                "description": "Mara confirms Lena faked her death",
                "planned_episode": 3,
                "mystery_id": "MYS_001",
                "depends_on": ["REV_001"],
                "audience_knowledge_before": "suspects",
                "audience_knowledge_after": "knows",
            },
        ],
        "escalation_milestones": [
            {"episode_number": 1, "escalation_level": 3, "description": "Mara discovers the letter"},
            {"episode_number": 2, "escalation_level": 6, "description": "Mara confronts her family"},
            {"episode_number": 3, "escalation_level": 9, "description": "Mara finds Lena alive"},
        ],
        "character_arc_milestones": [
            {
                "character_id": "CHAR_001",
                "episode_number": 1,
                "milestone": "Mara begins to doubt her grief",
                "arc_stage": "setup",
            },
            {
                "character_id": "CHAR_001",
                "episode_number": 3,
                "milestone": "Mara chooses to confront Lena",
                "arc_stage": "test",
            },
            {
                "character_id": "CHAR_002",
                "episode_number": 3,
                "milestone": "Lena is forced out of hiding",
                "arc_stage": "crisis",
            },
        ],
        "episode_assignments": [
            {
                "episode_number": 1,
                "act_number": 1,
                "objective": "Mara finds the letter",
                "reveals": ["REV_001"],
                "promises_setup": ["PROM_001"],
                "promises_paid_off": [],
                "escalation_level": 3,
                "character_milestones": ["Mara begins to doubt her grief"],
                "cliffhanger_type": "discovery",
            },
            {
                "episode_number": 2,
                "act_number": 2,
                "objective": "Mara investigates further",
                "reveals": [],
                "promises_setup": [],
                "promises_paid_off": [],
                "escalation_level": 6,
                "character_milestones": ["Mara suspects her family is hiding something"],
                "cliffhanger_type": "threat",
            },
            {
                "episode_number": 3,
                "act_number": 3,
                "objective": "Mara confronts Lena",
                "reveals": ["REV_002"],
                "promises_setup": [],
                "promises_paid_off": ["PROM_001"],
                "escalation_level": 9,
                "character_milestones": ["Mara chooses to confront Lena", "Lena is forced out of hiding"],
                "cliffhanger_type": "identity_reveal",
            },
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
