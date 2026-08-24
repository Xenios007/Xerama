"""Stage 2 - Series Bible generation. See docs/WORKFLOW.md Stage 2."""

from xerama.domain.brief import CreativeBrief
from xerama.domain.enums import ModelRole
from xerama.domain.story import ConceptCandidate, SeriesBible
from xerama.pipeline.ai_gateway import AIGateway

_SYSTEM_PROMPT = (
    "You are the Xerama story architect. Convert an approved microdrama "
    "concept into a complete Series Bible: the locked creative truth for the "
    "whole production. Be concrete and specific - locked_facts and "
    "world_rules must be checkable statements, not vague themes."
)


class BibleStage:
    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def generate_series_bible(
        self, brief: CreativeBrief, approved_concept: ConceptCandidate
    ) -> SeriesBible:
        prompt = (
            f"episode_count: {brief.episode_count}\n"
            f"episode_duration_seconds: {brief.episode_duration_seconds}\n"
            f"target_audience: {brief.target_audience}\n\n"
            f"Approved concept:\n{approved_concept.model_dump_json(indent=2)}"
        )
        return await self._gateway.generate(
            role=ModelRole.STORY_ARCHITECT,
            schema=SeriesBible,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
