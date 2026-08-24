from xerama.domain.enums import CliffhangerType, QCStatus
from xerama.domain.character import Character, CharacterCast
from xerama.domain.episode import Cliffhanger, DialogueLine, EpisodeOutline, EpisodeScript, ScriptScene
from xerama.domain.scene import Camera, EpisodeShotPlan, Scene, Shot
from xerama.pipeline.validators import ContinuityValidator, RetentionValidator


def _outline(**overrides) -> EpisodeOutline:
    base = dict(
        episode_number=1,
        objective="find the truth",
        opening_hook="a scream echoes through the empty apartment",
        stakes="her freedom",
        conflict="sister vs. sister",
        escalation=["she finds the letter", "she confronts Lena"],
        turn="the letter was a forgery",
        reveal="he was never who he claimed",
        duration_target_seconds=75,
        cliffhanger=Cliffhanger(type=CliffhangerType.IDENTITY_REVEAL, event="the mask comes off"),
    )
    base.update(overrides)
    return EpisodeOutline(**base)


def _script() -> EpisodeScript:
    return EpisodeScript(
        episode_number=1,
        title="Ep 1",
        scenes=[
            ScriptScene(
                scene_number=1,
                location="apartment",
                characters=["CHAR_001"],
                action="Mara reads the letter with shaking hands.",
                dialogue=[DialogueLine(character_id="CHAR_001", character_name="Mara", line="No...")],
            )
        ],
        estimated_duration_seconds=75,
    )


def _cast() -> CharacterCast:
    return CharacterCast(characters=[Character(id="CHAR_001", name="Mara", role="protagonist")])


def test_retention_validator_passes_healthy_outline() -> None:
    result = RetentionValidator().validate(_outline(), _script())
    assert result.status == QCStatus.PASS
    assert result.score == 10.0


def test_retention_validator_blocks_missing_hook_and_cliffhanger() -> None:
    outline = _outline(opening_hook="", cliffhanger=Cliffhanger(type=CliffhangerType.THREAT, event=""))
    result = RetentionValidator().validate(outline, _script())
    assert result.status == QCStatus.BLOCK
    assert any("opening_hook" in r for r in result.reasons)
    assert any("cliffhanger event" in r for r in result.reasons)


def test_retention_validator_warns_on_repeated_cliffhanger_type() -> None:
    outline = _outline(cliffhanger=Cliffhanger(type=CliffhangerType.THREAT, event="a gun in her hand"))
    result = RetentionValidator().validate(
        outline, _script(), recent_cliffhanger_types=[CliffhangerType.THREAT]
    )
    assert result.status == QCStatus.WARN
    assert any("repeats the previous episode" in r for r in result.reasons)


def test_retention_validator_warns_on_runtime_deviation() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apartment",
                shots=[
                    Shot(shot_number=1, scene_number=1, duration_seconds=3, camera=Camera(), action="a"),
                ],
            )
        ],
    )
    result = RetentionValidator().validate(_outline(duration_target_seconds=75), _script(), shot_plan=plan)
    assert result.status == QCStatus.WARN
    assert any("deviates" in r for r in result.reasons)


def test_continuity_validator_passes_when_all_characters_known() -> None:
    result = ContinuityValidator().validate(_cast(), _script())
    assert result.status == QCStatus.PASS


def test_continuity_validator_blocks_unknown_character_reference() -> None:
    script = _script()
    script.scenes[0].characters.append("CHAR_999")
    result = ContinuityValidator().validate(_cast(), script)
    assert result.status == QCStatus.BLOCK
    assert any("CHAR_999" in r for r in result.reasons)


def test_continuity_validator_blocks_unknown_dialogue_speaker() -> None:
    script = _script()
    script.scenes[0].dialogue.append(
        DialogueLine(character_id="CHAR_GHOST", character_name="Ghost", line="boo")
    )
    result = ContinuityValidator().validate(_cast(), script)
    assert result.status == QCStatus.BLOCK
    assert any("CHAR_GHOST" in r for r in result.reasons)


def test_continuity_validator_blocks_unknown_shot_character() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apartment",
                shots=[
                    Shot(
                        shot_number=1,
                        scene_number=1,
                        character_ids=["CHAR_999"],
                        duration_seconds=3,
                    )
                ],
            )
        ],
    )
    result = ContinuityValidator().validate(_cast(), _script(), shot_plan=plan)
    assert result.status == QCStatus.BLOCK
