"""Stage 1 - dual-candidate concept generation + AI judge.

See docs/WORKFLOW.md Stage 1, docs/ARCHITECTURE.md section 4, ADR-003.
"""

import asyncio

from xerama.domain.brief import CreativeBrief
from xerama.domain.enums import JudgeDecision, ModelRole
from xerama.domain.story import ConceptCandidate, JudgeResult
from xerama.pipeline.ai_gateway import AIGateway

_CONCEPT_SYSTEM_PROMPT = (
    "You are a microdrama concept generator for Xerama, an AI vertical-drama "
    "production system. Generate one complete, original serialized microdrama "
    "concept as JSON matching the given schema. Follow the emotional engine "
    "'Desire + Obstacle + Injustice + Secret + Reversal + Payoff'. The opening "
    "hook must create immediate curiosity or emotion within the first seconds."
)

_JUDGE_SYSTEM_PROMPT = (
    "You are the Xerama story judge. Compare two independently generated "
    "microdrama concepts against the same creative brief. Score each on hook, "
    "emotional_intensity, conflict, originality, serial_potential, "
    "reversal_potential, cliffhanger_potential, production_feasibility and "
    "character_potential (0-10). Decide A, B, or MERGE. If MERGE, give "
    "explicit merge_instructions describing exactly what to take from each "
    "candidate. Never silently discard a candidate's strengths."
)

_MERGE_SYSTEM_PROMPT = (
    "You are the Xerama concept synthesizer. Combine two microdrama concept "
    "candidates into one coherent concept, following the merge instructions "
    "exactly. Output must match the ConceptCandidate schema."
)


def _brief_prompt(brief: CreativeBrief, slot_label: str) -> str:
    return (
        f"Creative brief (candidate {slot_label}):\n"
        f"genre: {brief.genre}\n"
        f"premise seed: {brief.premise or '(none supplied - propose one)'}\n"
        f"target_audience: {brief.target_audience}\n"
        f"tone: {brief.tone or '(unspecified)'}\n"
        f"episode_count: {brief.episode_count}\n"
        f"episode_duration_seconds: {brief.episode_duration_seconds}\n"
        f"content_restrictions: {brief.content_restrictions or 'none'}\n"
        "Generate an independent, original concept. Do not assume what any "
        "other candidate might contain."
    )


class ConceptStage:
    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def generate_candidates(
        self, brief: CreativeBrief
    ) -> tuple[ConceptCandidate, ConceptCandidate]:
        """Two independent candidate generations, run concurrently. Both are
        returned regardless of which the judge later prefers - see ADR-019."""

        candidate_a, candidate_b = await asyncio.gather(
            self._gateway.generate(
                role=ModelRole.CONCEPT_GENERATOR_A,
                schema=ConceptCandidate,
                system_prompt=_CONCEPT_SYSTEM_PROMPT,
                user_prompt=_brief_prompt(brief, "A"),
            ),
            self._gateway.generate(
                role=ModelRole.CONCEPT_GENERATOR_B,
                schema=ConceptCandidate,
                system_prompt=_CONCEPT_SYSTEM_PROMPT,
                user_prompt=_brief_prompt(brief, "B"),
            ),
        )
        return candidate_a, candidate_b

    async def judge(
        self, brief: CreativeBrief, candidate_a: ConceptCandidate, candidate_b: ConceptCandidate
    ) -> JudgeResult:
        prompt = (
            f"Creative brief: genre={brief.genre}, audience={brief.target_audience}, "
            f"episode_count={brief.episode_count}.\n\n"
            f"Candidate A:\n{candidate_a.model_dump_json(indent=2)}\n\n"
            f"Candidate B:\n{candidate_b.model_dump_json(indent=2)}"
        )
        return await self._gateway.generate(
            role=ModelRole.JUDGE,
            schema=JudgeResult,
            system_prompt=_JUDGE_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

    async def resolve_approved_concept(
        self,
        candidate_a: ConceptCandidate,
        candidate_b: ConceptCandidate,
        judge_result: JudgeResult,
    ) -> ConceptCandidate:
        if judge_result.decision == JudgeDecision.A:
            return candidate_a
        if judge_result.decision == JudgeDecision.B:
            return candidate_b

        prompt = (
            f"Candidate A:\n{candidate_a.model_dump_json(indent=2)}\n\n"
            f"Candidate B:\n{candidate_b.model_dump_json(indent=2)}\n\n"
            f"Merge instructions:\n{judge_result.merge_instructions.model_dump_json(indent=2)}\n\n"
            f"Judge reasoning: {judge_result.reason}"
        )
        return await self._gateway.generate(
            role=ModelRole.STORY_ARCHITECT,
            schema=ConceptCandidate,
            system_prompt=_MERGE_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
