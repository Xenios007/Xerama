import fixtures as fx
from xerama.domain.character import CharacterCast
from xerama.domain.scene import Camera, EpisodeShotPlan, ProviderRequirements, Scene, Shot, Visual
from xerama.domain.story import SeriesBible
from xerama.domain.style_bible import StyleBible
from xerama.pipeline.prompt_compiler import DEFAULT_NEGATIVE_CONSTRAINTS, PromptCompiler


def _bible() -> SeriesBible:
    return SeriesBible.model_validate(fx.bible())


def _cast() -> CharacterCast:
    return CharacterCast.model_validate(fx.cast())


def _scene_with_shot(**shot_overrides) -> Scene:
    base = dict(
        shot_number=1,
        scene_number=1,
        duration_seconds=5.0,
        character_ids=["CHAR_001"],
        action="Mara opens the letter",
        dialogue="This can't be real.",
        camera=Camera(shot_size="close-up", angle="eye-level", lens="50mm", movement="static"),
        visual=Visual(composition="centered", lighting="low-key", emotion="dread"),
    )
    base.update(shot_overrides)
    return Scene(scene_number=1, location="apartment", time_of_day="night", shots=[Shot(**base)])


def test_compile_shot_is_deterministic() -> None:
    scene = _scene_with_shot()
    compiler = PromptCompiler()
    request_a = compiler.compile_shot(scene.shots[0], scene, _cast(), _bible())
    request_b = compiler.compile_shot(scene.shots[0], scene, _cast(), _bible())
    assert request_a == request_b
    assert request_a.prompt == request_b.prompt


def test_compile_shot_includes_negative_constraints() -> None:
    scene = _scene_with_shot()
    request = PromptCompiler().compile_shot(scene.shots[0], scene, _cast(), _bible())
    for constraint in DEFAULT_NEGATIVE_CONSTRAINTS:
        assert constraint in request.negative_prompt


def test_compile_shot_prompt_includes_action_dialogue_and_location() -> None:
    scene = _scene_with_shot()
    request = PromptCompiler().compile_shot(scene.shots[0], scene, _cast(), _bible())
    assert "apartment" in request.prompt
    assert "Mara opens the letter" in request.prompt
    assert "This can't be real." in request.prompt
    assert "Mara (protagonist)" in request.prompt
    assert "9:16" in request.prompt


def test_compile_shot_reference_selection_uses_visual_identity_id_when_present() -> None:
    cast = _cast()
    cast.characters[0].visual_identity_id = "ASSET_MARA_ROOT"
    scene = _scene_with_shot()
    request = PromptCompiler().compile_shot(scene.shots[0], scene, cast, _bible())
    assert request.references.character_asset_ids == ["ASSET_MARA_ROOT"]


def test_compile_shot_reference_selection_falls_back_to_character_id() -> None:
    scene = _scene_with_shot()
    request = PromptCompiler().compile_shot(scene.shots[0], scene, _cast(), _bible())
    assert request.references.character_asset_ids == ["CHAR_001"]


def test_compile_shot_carries_continuity_group_and_provider_requirements() -> None:
    scene = _scene_with_shot(
        continuity_group="GRP_A", provider_requirements=ProviderRequirements(native_audio_required=True)
    )
    request = PromptCompiler().compile_shot(scene.shots[0], scene, _cast(), _bible())
    assert request.continuity_group == "GRP_A"
    assert request.provider_requirements.native_audio_required is True


def test_compile_episode_returns_one_request_per_shot() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            _scene_with_shot(),
            Scene(
                scene_number=2,
                location="street",
                shots=[
                    Shot(shot_number=1, scene_number=2, duration_seconds=4.0),
                    Shot(shot_number=2, scene_number=2, duration_seconds=4.0),
                ],
            ),
        ],
    )
    requests = PromptCompiler().compile_episode(plan, _cast(), _bible())
    assert len(requests) == 3
    assert [r.scene_number for r in requests] == [1, 2, 2]


def test_compile_shot_uses_style_bible_dna_and_negatives_when_supplied() -> None:
    scene = _scene_with_shot()
    style_bible = StyleBible(
        id="SB_1",
        series_id="SER_1",
        style_asset_id="ASSET_STYLE_ROOT",
        style_dna="high-contrast neon noir",
        negatives=["oversaturated pastel palette"],
    )
    request = PromptCompiler().compile_shot(scene.shots[0], scene, _cast(), _bible(), style_bible)
    assert request.style_dna == "high-contrast neon noir"
    assert "oversaturated pastel palette" in request.negative_prompt
    for constraint in DEFAULT_NEGATIVE_CONSTRAINTS:
        assert constraint in request.negative_prompt
    assert request.references.style_asset_id == "ASSET_STYLE_ROOT"


def test_compile_shot_shot_level_style_asset_overrides_style_bible() -> None:
    from xerama.domain.scene import ShotReferences

    scene = _scene_with_shot(references=ShotReferences(style_asset_id="ASSET_SHOT_STYLE"))
    style_bible = StyleBible(id="SB_1", series_id="SER_1", style_asset_id="ASSET_SERIES_STYLE")
    request = PromptCompiler().compile_shot(scene.shots[0], scene, _cast(), _bible(), style_bible)
    assert request.references.style_asset_id == "ASSET_SHOT_STYLE"


def test_compile_shot_without_style_bible_matches_prior_behavior() -> None:
    scene = _scene_with_shot()
    request = PromptCompiler().compile_shot(scene.shots[0], scene, _cast(), _bible())
    assert request.style_dna == ""
    assert request.references.style_asset_id is None


def test_character_dna_formats_from_structured_fields_when_present() -> None:
    cast = _cast()
    cast.characters[0].character_dna.eyes = "brown"
    cast.characters[0].character_dna.hairstyle = "long wavy"
    scene = _scene_with_shot()
    request = PromptCompiler().compile_shot(scene.shots[0], scene, cast, _bible())
    assert "brown" in request.character_dna[0]
    assert "long wavy" in request.character_dna[0]
