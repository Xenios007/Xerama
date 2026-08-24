from xerama.domain.enums import BlockingDepth, ScreenPosition
from xerama.domain.scene import CharacterBlock, MovementBeat, SceneBlocking, Shot


def test_character_block_defaults() -> None:
    block = CharacterBlock(character_id="CHAR_001")
    assert block.position == ScreenPosition.CENTER
    assert block.depth == BlockingDepth.MIDGROUND
    assert block.visible is True
    assert block.speaking is False
    assert block.occluded_by == []


def test_shot_blocking_plan_defaults_to_none() -> None:
    shot = Shot(shot_number=1, scene_number=1, duration_seconds=5.0)
    assert shot.blocking_plan is None
    assert shot.blocking == ""


def test_scene_blocking_round_trips_through_json() -> None:
    plan = SceneBlocking(
        characters=[
            CharacterBlock(character_id="CHAR_001", position=ScreenPosition.LEFT, speaking=True),
            CharacterBlock(
                character_id="CHAR_002",
                position=ScreenPosition.RIGHT,
                depth=BlockingDepth.BACKGROUND,
                occluded_by=["CHAR_001"],
            ),
        ],
        movement_beats=[
            MovementBeat(
                start_seconds=0.0,
                end_seconds=2.0,
                character_id="CHAR_001",
                description="crosses to center",
                from_position=ScreenPosition.LEFT,
                to_position=ScreenPosition.CENTER,
            )
        ],
        screen_direction="left_to_right",
    )
    restored = SceneBlocking.model_validate_json(plan.model_dump_json())
    assert restored.screen_direction == "left_to_right"
    assert restored.characters[1].occluded_by == ["CHAR_001"]
    assert restored.movement_beats[0].to_position == ScreenPosition.CENTER
