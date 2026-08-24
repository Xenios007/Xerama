"""Season & Reveal Engine stage (XER-006, Module 01).

Converts an approved Series Bible + cast into a validated macro-story plan
for the requested episode count, sitting between series-foundation
generation and per-episode outline generation - see
docs/WORKFLOW.md Stage 3 "Season Architecture".
"""

from xerama.domain.character import CharacterCast
from xerama.domain.enums import ModelRole
from xerama.domain.season import SeasonPlan
from xerama.domain.story import SeriesBible
from xerama.pipeline.ai_gateway import AIGateway

_SYSTEM_PROMPT = (
    "You are the Xerama season architect. Design the macro story structure "
    "for the full requested episode count: acts/phases, a reveal ladder, "
    "mysteries, promises/payoffs, an escalation curve and character-arc "
    "milestones, then assign every episode number to this structure. "
    "Follow docs/STORY_FORMULA.md's ladder: Question -> Partial Answer -> "
    "New Problem -> Reversal -> Bigger Question -> Escalation -> Payoff. "
    "Rules: every reveal must come after the mystery it resolves was "
    "introduced and after any reveal it depends on; every promise's payoff "
    "episode (if planned within the season) must come after its setup "
    "episode; escalation must trend upward across the season; do not repeat "
    "the same cliffhanger type in back-to-back episodes; give every "
    "character at least one arc milestone; leave at least one mystery or "
    "promise deliberately open at the end unless this is a series finale."
)


class SeasonStage:
    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def generate_season_plan(
        self, bible: SeriesBible, cast: CharacterCast, episode_count: int, feedback: str = ""
    ) -> SeasonPlan:
        prompt = (
            f"Series Bible:\n{bible.model_dump_json(indent=2)}\n\n"
            f"Cast:\n{cast.model_dump_json(indent=2)}\n\n"
            f"Produce a season plan for exactly {episode_count} episodes "
            f"(episode_number 1..{episode_count}, each assigned exactly once)."
        )
        if feedback:
            prompt += (
                "\n\nThe previous season plan was rejected by validation for: "
                f"{feedback}. Fix these issues explicitly."
            )
        return await self._gateway.generate(
            role=ModelRole.STORY_ARCHITECT,
            schema=SeasonPlan,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
