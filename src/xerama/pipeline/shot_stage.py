"""Stage 7 - Director Engine: script -> structured scenes/shots.

See docs/ARCHITECTURE.md section 9 (Shot Contract) and ADR-015 (vertical
drama directing preset). No media generation happens here - this only plans
the shots that a later Media Engine would render.
"""

from xerama.domain.enums import ModelRole
from xerama.domain.episode import EpisodeScript
from xerama.domain.scene import EpisodeShotPlan
from xerama.pipeline.ai_gateway import AIGateway

_SYSTEM_PROMPT = (
    "You are the Xerama Director. Convert the episode script into a "
    "structured shot list, one Scene per script scene, split into individual "
    "Shots (typically 5-15 seconds each, per "
    "research/PRODUCTION_STACK_2026.md). Rules: "
    "(1) compose for 9:16 vertical - readable close/medium shots, deliberate "
    "headroom, avoid wide horizontal staging; "
    "(2) multi-speaker dialogue needs coverage - alternate speaker "
    "single/reaction/insert shots rather than one long two-shot; "
    "(3) each shot must advance an event, revelation or emotional change; "
    "(4) set narrative_function, camera (shot_size/angle/lens/movement) and "
    "visual (composition/lighting/emotion) for every shot; "
    "(5) use micro_beats only when a shot's action clearly changes partway "
    "through the clip; "
    "(6) set blocking only as a short free-text note on character/camera "
    "position when it matters (e.g. 'A left, B right, A closer to camera') - "
    "leave it empty otherwise, do not invent a coordinate system; "
    "(7) give adjacent shots that must stay visually continuous (e.g. a "
    "continuous conversation or an action carrying across cuts) the same "
    "continuity_group string; independent shots (different scene, time "
    "jump, or cutaway) must leave continuity_group null; "
    "(8) set provider_requirements per shot: image_to_video should stay "
    "true for nearly every shot (Xerama generates from an approved "
    "keyframe); set first_frame_required true unless the shot is a pure "
    "establishing/transition shot; set last_frame_required true only for a "
    "shot that is NOT the last in its continuity_group (its final frame "
    "anchors the next shot); set subject_reference_required true whenever "
    "named characters appear; set native_audio_required true only if the "
    "shot needs synchronized dialogue/audio baked into the generated clip."
)


class ShotStage:
    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def plan_shots(self, script: EpisodeScript, feedback: str = "") -> EpisodeShotPlan:
        prompt = f"Episode script:\n{script.model_dump_json(indent=2)}"
        if feedback:
            prompt += (
                "\n\nThe previous shot plan was rejected by continuity QC for: "
                f"{feedback}. Fix these issues explicitly - only reference "
                "characters and locations that actually appear in the script above."
            )
        return await self._gateway.generate(
            role=ModelRole.SHOT_PLANNER,
            schema=EpisodeShotPlan,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
