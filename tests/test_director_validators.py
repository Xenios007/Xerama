from xerama.domain.enums import QCStatus
from xerama.domain.episode import DialogueLine, EpisodeScript, ScriptScene
from xerama.domain.scene import Camera, EpisodeShotPlan, ProviderRequirements, Scene, Shot, Visual
from xerama.pipeline.director_validators import DirectorValidator


def _shot(**overrides) -> Shot:
    base = dict(
        shot_number=1,
        scene_number=1,
        duration_seconds=5.0,
        camera=Camera(shot_size="close-up"),
        visual=Visual(composition="centered"),
        character_ids=["CHAR_001"],
    )
    base.update(overrides)
    return Shot(**base)


def test_vertical_composition_passes_when_every_shot_declares_framing() -> None:
    plan = EpisodeShotPlan(episode_number=1, scenes=[Scene(scene_number=1, location="apt", shots=[_shot()])])
    result = DirectorValidator().check_vertical_composition(plan)
    assert result.status == QCStatus.PASS


def test_vertical_composition_warns_on_missing_shot_size() -> None:
    shot = _shot(camera=Camera(shot_size=""))
    plan = EpisodeShotPlan(episode_number=1, scenes=[Scene(scene_number=1, location="apt", shots=[shot])])
    result = DirectorValidator().check_vertical_composition(plan)
    assert result.status == QCStatus.WARN
    assert any("no camera.shot_size" in r for r in result.reasons)


def test_vertical_composition_warns_on_crowded_shot_without_wide_framing() -> None:
    shot = _shot(character_ids=["CHAR_001", "CHAR_002", "CHAR_003"], camera=Camera(shot_size="close-up"))
    plan = EpisodeShotPlan(episode_number=1, scenes=[Scene(scene_number=1, location="apt", shots=[shot])])
    result = DirectorValidator().check_vertical_composition(plan)
    assert result.status == QCStatus.WARN
    assert any("crowding risk" in r for r in result.reasons)


def _script_with_two_speakers() -> EpisodeScript:
    return EpisodeScript(
        episode_number=1,
        title="Ep 1",
        scenes=[
            ScriptScene(
                scene_number=1,
                location="apt",
                characters=["CHAR_001", "CHAR_002"],
                action="Mara confronts Lena.",
                dialogue=[
                    DialogueLine(character_id="CHAR_001", character_name="Mara", line="You lied."),
                    DialogueLine(character_id="CHAR_002", character_name="Lena", line="I had no choice."),
                ],
            )
        ],
        estimated_duration_seconds=30,
    )


def test_dialogue_coverage_passes_with_single_shots() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apt",
                shots=[
                    _shot(shot_number=1, character_ids=["CHAR_001"]),
                    _shot(shot_number=2, character_ids=["CHAR_002"]),
                ],
            )
        ],
    )
    result = DirectorValidator().check_dialogue_coverage(_script_with_two_speakers(), plan)
    assert result.status == QCStatus.PASS


def test_dialogue_coverage_warns_when_every_shot_keeps_both_speakers() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apt",
                shots=[_shot(shot_number=1, character_ids=["CHAR_001", "CHAR_002"])],
            )
        ],
    )
    result = DirectorValidator().check_dialogue_coverage(_script_with_two_speakers(), plan)
    assert result.status == QCStatus.WARN
    assert any("no single/reaction coverage" in r for r in result.reasons)


def test_dialogue_coverage_warns_when_scene_has_no_shots_planned() -> None:
    plan = EpisodeShotPlan(episode_number=1, scenes=[])
    result = DirectorValidator().check_dialogue_coverage(_script_with_two_speakers(), plan)
    assert result.status == QCStatus.WARN
    assert any("no shots planned" in r for r in result.reasons)


def test_continuity_grouping_passes_for_contiguous_group() -> None:
    shots = [
        _shot(shot_number=1, continuity_group="GRP_A", provider_requirements=ProviderRequirements(last_frame_required=True)),
        _shot(shot_number=2, continuity_group="GRP_A", provider_requirements=ProviderRequirements(last_frame_required=False)),
    ]
    plan = EpisodeShotPlan(episode_number=1, scenes=[Scene(scene_number=1, location="apt", shots=shots)])
    result = DirectorValidator().check_continuity_grouping(plan)
    assert result.status == QCStatus.PASS


def test_continuity_grouping_blocks_non_contiguous_group() -> None:
    shots = [
        _shot(shot_number=1, continuity_group="GRP_A"),
        _shot(shot_number=2, continuity_group=None),
        _shot(shot_number=3, continuity_group="GRP_A"),
    ]
    plan = EpisodeShotPlan(episode_number=1, scenes=[Scene(scene_number=1, location="apt", shots=shots)])
    result = DirectorValidator().check_continuity_grouping(plan)
    assert result.status == QCStatus.BLOCK
    assert any("not a contiguous" in r for r in result.reasons)


def test_continuity_grouping_warns_when_mid_group_shot_missing_last_frame_flag() -> None:
    shots = [
        _shot(shot_number=1, continuity_group="GRP_A", provider_requirements=ProviderRequirements(last_frame_required=False)),
        _shot(shot_number=2, continuity_group="GRP_A", provider_requirements=ProviderRequirements(last_frame_required=False)),
    ]
    plan = EpisodeShotPlan(episode_number=1, scenes=[Scene(scene_number=1, location="apt", shots=shots)])
    result = DirectorValidator().check_continuity_grouping(plan)
    assert result.status == QCStatus.WARN
    assert any("last_frame_required is false" in r for r in result.reasons)
