"""Stage 4/5 - episode outline (beat sheet) and script generation.

See docs/WORKFLOW.md Stages 4-5. Only Episode 1 gets a full script in the
XER-001 milestone; outlines are generated for the requested episode count so
the season/reveal ladder is visible even though later scripts are deferred.
"""

from xerama.domain.canon import CanonSnapshot
from xerama.domain.character import CharacterCast
from xerama.domain.enums import ModelRole
from xerama.domain.episode import EpisodeOutline, EpisodeOutlineSet, EpisodeScript
from xerama.domain.story import SeriesBible
from xerama.pipeline.ai_gateway import AIGateway

_OUTLINE_SYSTEM_PROMPT = (
    "You are the Xerama story architect. Generate a beat-sheet outline for "
    "each requested episode number, forming a reveal/escalation ladder per "
    "docs/STORY_FORMULA.md section 4 (Question -> Partial Answer -> New "
    "Problem -> Reversal -> Bigger Question -> Escalation -> Payoff). Rotate "
    "cliffhanger types across episodes - do not repeat the same type twice in "
    "a row. Every episode must end genuinely unresolved."
)

_SCRIPT_SYSTEM_PROMPT = (
    "You are the Xerama episode writer. Convert the approved beat sheet into "
    "a full vertical-microdrama script: compact dialogue, an event or "
    "emotional change in nearly every scene, escalating conflict, and a "
    "cliffhanger ending that matches the outline's cliffhanger. Characters "
    "may only reference facts already established in the supplied canon "
    "context - do not leak future reveals early. Respect the duration budget."
)


class EpisodeStage:
    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def generate_outlines(
        self, bible: SeriesBible, cast: CharacterCast, episode_count: int
    ) -> list[EpisodeOutline]:
        prompt = (
            f"Series Bible:\n{bible.model_dump_json(indent=2)}\n\n"
            f"Cast:\n{cast.model_dump_json(indent=2)}\n\n"
            f"Generate exactly {episode_count} outlines, episode_number 1..{episode_count}."
        )
        result = await self._gateway.generate(
            role=ModelRole.STORY_ARCHITECT,
            schema=EpisodeOutlineSet,
            system_prompt=_OUTLINE_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
        return result.outlines

    async def generate_script(
        self,
        bible: SeriesBible,
        cast: CharacterCast,
        outline: EpisodeOutline,
        canon: CanonSnapshot,
    ) -> EpisodeScript:
        prompt = (
            f"Series Bible:\n{bible.model_dump_json(indent=2)}\n\n"
            f"Cast:\n{cast.model_dump_json(indent=2)}\n\n"
            f"Approved outline for this episode:\n{outline.model_dump_json(indent=2)}\n\n"
            f"Canonical context available to this episode:\n{canon.model_dump_json(indent=2)}"
        )
        return await self._gateway.generate(
            role=ModelRole.EPISODE_WRITER,
            schema=EpisodeScript,
            system_prompt=_SCRIPT_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
