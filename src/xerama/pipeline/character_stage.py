"""Stage 2b - character and relationship generation.

See docs/WORKFLOW.md Stage 2, research/CHARACTER_CONTINUITY_PLAYBOOK.md.
Only the textual/structural identity layer is generated here - no root
reference images or voices yet (deferred per docs/ARCHITECTURE.md section 8).
"""

from xerama.domain.character import CharacterCast
from xerama.domain.enums import ModelRole
from xerama.domain.story import SeriesBible
from xerama.pipeline.ai_gateway import AIGateway

_SYSTEM_PROMPT = (
    "You are the Xerama character architect. Generate the principal cast for "
    "this series bible: 2-3 main characters (per "
    "research/CHARACTER_CONTINUITY_PLAYBOOK.md Trial 01 guidance - keep the "
    "cast small), each with a stable `id` (e.g. CHAR_001) referenced "
    "consistently, plus their relationships to each other. Every character "
    "needs a concrete goal, fear, flaw and secret - avoid generic traits."
)


class CharacterStage:
    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def generate_cast(self, bible: SeriesBible) -> CharacterCast:
        prompt = f"Series Bible:\n{bible.model_dump_json(indent=2)}"
        return await self._gateway.generate(
            role=ModelRole.STORY_ARCHITECT,
            schema=CharacterCast,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
