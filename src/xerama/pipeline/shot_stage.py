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
    "through the clip."
)


class ShotStage:
    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def plan_shots(self, script: EpisodeScript) -> EpisodeShotPlan:
        prompt = f"Episode script:\n{script.model_dump_json(indent=2)}"
        return await self._gateway.generate(
            role=ModelRole.SHOT_PLANNER,
            schema=EpisodeShotPlan,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
