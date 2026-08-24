"""Provider-neutral Prompt Compiler (Module 03).

Pure/deterministic: the same shot + scene + cast + bible always compiles to
the same `ShotGenerationRequest`. No LLM call, no randomness - reproducible
prompt compilation is required for benchmarking/model swapping (see
research/WIND_COMIC_DEEP_DIVE.md section 23) and is directly exercised by
the determinism tests.
"""

from xerama.domain.character import Character, CharacterCast
from xerama.domain.generation_request import CompiledReferences, ShotGenerationRequest
from xerama.domain.scene import EpisodeShotPlan, Scene, Shot
from xerama.domain.story import SeriesBible

# A stable, deterministic default negative-constraint set. Real per-project
# negatives (from a Style Bible - Module 06) can be appended later; this is
# the provider-neutral baseline every shot compiles with today.
DEFAULT_NEGATIVE_CONSTRAINTS: tuple[str, ...] = (
    "extra limbs",
    "deformed hands",
    "text artifacts",
    "watermark or logo",
    "off-model/inconsistent character face",
    "wardrobe inconsistent with prior shots",
    "horizontal letterboxing",
)


class PromptCompiler:
    def compile_episode(
        self, plan: EpisodeShotPlan, cast: CharacterCast, bible: SeriesBible
    ) -> list[ShotGenerationRequest]:
        return [
            self.compile_shot(shot, scene, cast, bible)
            for scene in plan.scenes
            for shot in scene.shots
        ]

    def compile_shot(
        self, shot: Shot, scene: Scene, cast: CharacterCast, bible: SeriesBible
    ) -> ShotGenerationRequest:
        characters_in_shot = [c for c in cast.characters if c.id in shot.character_ids]

        return ShotGenerationRequest(
            shot_number=shot.shot_number,
            scene_number=scene.scene_number,
            prompt=self._compose_prompt(shot, scene, characters_in_shot, bible),
            negative_prompt=", ".join(DEFAULT_NEGATIVE_CONSTRAINTS),
            character_dna=[self._format_character_dna(c) for c in characters_in_shot],
            style_dna="",  # populated once a Style Bible exists (Module 06)
            duration_seconds=shot.duration_seconds,
            camera=shot.camera,
            visual=shot.visual,
            blocking=shot.blocking,
            audio_mode=shot.audio_mode,
            references=CompiledReferences(
                character_asset_ids=[c.visual_identity_id or c.id for c in characters_in_shot],
                style_asset_id=shot.references.style_asset_id,
                location_asset_id=shot.references.location_asset_id,
                prop_asset_ids=shot.references.prop_asset_ids,
                continuity_frame_asset_id=shot.references.previous_continuity_frame_asset_id,
            ),
            provider_requirements=shot.provider_requirements,
            continuity_group=shot.continuity_group,
        )

    def _format_character_dna(self, character: Character) -> str:
        dna = character.character_dna
        parts = [
            p
            for p in (
                dna.eyes,
                dna.face_shape,
                dna.nose,
                dna.mouth,
                dna.hairstyle,
                dna.hair_color,
                dna.skin_tone,
                dna.signature_outfit,
            )
            if p
        ]
        signature = ", ".join(parts) if parts else character.description
        return f"{character.name}: {signature}" if signature else character.name

    def _compose_prompt(
        self, shot: Shot, scene: Scene, characters: list[Character], bible: SeriesBible
    ) -> str:
        segments = [f"{bible.title} - {scene.location}, {scene.time_of_day or 'unspecified time'}."]
        if characters:
            segments.append(
                "Characters: " + "; ".join(f"{c.name} ({c.role})" for c in characters) + "."
            )
        if shot.blocking:
            segments.append(f"Blocking: {shot.blocking}.")
        if shot.action:
            segments.append(shot.action.rstrip(".") + ".")
        if shot.dialogue:
            segments.append(f'Dialogue: "{shot.dialogue}"')
        segments.append(
            f"Camera: {shot.camera.shot_size or 'medium shot'}, {shot.camera.angle or 'eye-level'}, "
            f"{shot.camera.lens or 'standard lens'}, {shot.camera.movement or 'static'}."
        )
        segments.append(
            f"Visual: {shot.visual.composition or 'centered'} composition, "
            f"{shot.visual.lighting or 'natural'} lighting, {shot.visual.emotion or 'neutral'} emotional tone."
        )
        segments.append(
            "Vertical 9:16 framing, readable close/medium subject scale, headroom preserved, "
            "subtitle-safe lower third clear."
        )
        return " ".join(segments)
