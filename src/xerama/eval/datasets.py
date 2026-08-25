"""Versioned evaluation dataset (MODULE-072).

Covers the roles that actually make an LLM call in this codebase today
(`CONCEPT_GENERATOR_A`/`_B`, `JUDGE`, `EPISODE_WRITER` - "concepts,
judge, ... and scripts"). `CONTINUITY_CHECKER` is deliberately absent:
`ModelRole.CONTINUITY_CHECKER` is defined in the config/enum but no
pipeline stage ever calls `AIGateway.generate(role=CONTINUITY_CHECKER,
...)` - continuity validation is a deterministic check
(`pipeline/director_validators.py`/`pipeline/validators.py`), not an
LLM call, matching this codebase's established "deterministic
heuristics preferred over LLM calls" pattern (see e.g. MODULE-063/065's
same choice). There is nothing to benchmark until a real LLM-based
continuity role is added; `eval_harness.py`'s `EvalCase`/`EvalHarness`
are role-generic, so that role plugs into this exact framework with a
new dataset entry, no framework change, if one is ever built.

`DATASET_VERSION` bumps whenever a case's prompt or expected shape
changes - `EvalRunResult.dataset_version` records which version produced
a given result, so results from different dataset versions are never
silently compared as if they were the same benchmark (ADR-010's
"preserve enough metadata to reconstruct AI decisions" applied to
evals).
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from xerama.domain.enums import ModelRole
from xerama.domain.episode import EpisodeScript
from xerama.domain.story import ConceptCandidate, JudgeResult

DATASET_VERSION = "v1"


@dataclass(frozen=True)
class EvalCase:
    id: str
    role: ModelRole
    schema: type[BaseModel]
    name: str
    system_prompt: str
    user_prompt: str
    description: str = ""
    # Optional per-case expectations the quality rubric (eval_quality.py)
    # can check against - e.g. an episode script's target runtime.
    expectations: dict[str, Any] = field(default_factory=dict)


_CONCEPT_SYSTEM_PROMPT = (
    "You are a microdrama concept generator. Given a genre and premise seed, "
    "produce one complete, original vertical-drama concept as JSON matching "
    "the ConceptCandidate schema. Every field must be filled in with "
    "specific, concrete content - no placeholders."
)

CONCEPT_GENERATOR_CASES: list[EvalCase] = [
    EvalCase(
        id="concept-revenge-thriller",
        role=ModelRole.CONCEPT_GENERATOR_A,
        schema=ConceptCandidate,
        name="Revenge thriller seed",
        system_prompt=_CONCEPT_SYSTEM_PROMPT,
        user_prompt=(
            "Genre: revenge thriller. Premise seed: a woman returns to her "
            "hometown for her sister's funeral and discovers the death was "
            "not an accident."
        ),
    ),
    EvalCase(
        id="concept-forbidden-romance",
        role=ModelRole.CONCEPT_GENERATOR_A,
        schema=ConceptCandidate,
        name="Forbidden romance seed",
        system_prompt=_CONCEPT_SYSTEM_PROMPT,
        user_prompt=(
            "Genre: forbidden romance. Premise seed: two rival family heirs "
            "are secretly married and must hide it during a hostile "
            "corporate merger."
        ),
    ),
    EvalCase(
        id="concept-supernatural-mystery",
        role=ModelRole.CONCEPT_GENERATOR_A,
        schema=ConceptCandidate,
        name="Supernatural mystery seed",
        system_prompt=_CONCEPT_SYSTEM_PROMPT,
        user_prompt=(
            "Genre: supernatural mystery. Premise seed: a woman starts "
            "receiving voicemails from her own phone number, a week in the "
            "future."
        ),
    ),
]

_JUDGE_SYSTEM_PROMPT = (
    "You are the creative judge for a microdrama pipeline. Compare two "
    "concept candidates and output a JudgeResult JSON: decide A, B, or "
    "MERGE, score each candidate 0-10 on every criterion, and give a "
    "specific reason for the decision."
)

JUDGE_CASES: list[EvalCase] = [
    EvalCase(
        id="judge-clear-a-winner",
        role=ModelRole.JUDGE,
        schema=JudgeResult,
        name="Clear A winner",
        system_prompt=_JUDGE_SYSTEM_PROMPT,
        user_prompt=(
            "Candidate A: a tightly-plotted revenge thriller with a strong "
            "opening hook and a serialized mystery engine.\n"
            "Candidate B: a generic breakup drama with no clear conflict "
            "or hook.\n"
            "Which is the stronger vertical-drama concept?"
        ),
    ),
    EvalCase(
        id="judge-clear-b-winner",
        role=ModelRole.JUDGE,
        schema=JudgeResult,
        name="Clear B winner",
        system_prompt=_JUDGE_SYSTEM_PROMPT,
        user_prompt=(
            "Candidate A: a slow-moving family drama with no cliffhanger "
            "potential.\n"
            "Candidate B: a forbidden-romance thriller with a strong "
            "secret-marriage hook and clear escalating stakes.\n"
            "Which is the stronger vertical-drama concept?"
        ),
    ),
    EvalCase(
        id="judge-merge-candidate",
        role=ModelRole.JUDGE,
        schema=JudgeResult,
        name="Merge-worthy pair",
        system_prompt=_JUDGE_SYSTEM_PROMPT,
        user_prompt=(
            "Candidate A: a supernatural mystery with an excellent hook "
            "(voicemails from the future) but a weak, underdeveloped cast.\n"
            "Candidate B: a supernatural mystery with a strong ensemble "
            "cast and emotional core but a forgettable, generic hook.\n"
            "Which is the stronger vertical-drama concept, or should they "
            "be merged?"
        ),
    ),
]

_EPISODE_WRITER_SYSTEM_PROMPT = (
    "You are the episode script writer for a vertical microdrama. Write a "
    "full episode script as JSON matching the EpisodeScript schema: at "
    "least two scenes, each with concrete action and at least one line of "
    "dialogue, targeting the given runtime."
)

EPISODE_WRITER_CASES: list[EvalCase] = [
    EvalCase(
        id="script-cold-open-reveal",
        role=ModelRole.EPISODE_WRITER,
        schema=EpisodeScript,
        name="Cold-open reveal episode",
        system_prompt=_EPISODE_WRITER_SYSTEM_PROMPT,
        user_prompt=(
            "Episode 1 of a revenge thriller. Mara returns home for her "
            "sister's funeral and finds a note proving it wasn't an "
            "accident. Target runtime: 75 seconds. End on a cliffhanger."
        ),
        expectations={"target_duration_seconds": 75.0, "min_scenes": 2},
    ),
    EvalCase(
        id="script-secret-marriage-tension",
        role=ModelRole.EPISODE_WRITER,
        schema=EpisodeScript,
        name="Secret-marriage tension episode",
        system_prompt=_EPISODE_WRITER_SYSTEM_PROMPT,
        user_prompt=(
            "Episode 3 of a forbidden-romance drama. The two secretly-"
            "married rivals must sit across from each other in a merger "
            "negotiation without revealing their relationship. Target "
            "runtime: 90 seconds."
        ),
        expectations={"target_duration_seconds": 90.0, "min_scenes": 2},
    ),
]

_CASES_BY_ROLE: dict[ModelRole, list[EvalCase]] = {
    ModelRole.CONCEPT_GENERATOR_A: CONCEPT_GENERATOR_CASES,
    ModelRole.JUDGE: JUDGE_CASES,
    ModelRole.EPISODE_WRITER: EPISODE_WRITER_CASES,
}


def cases_for_role(role: ModelRole) -> list[EvalCase]:
    """Empty list (not an error) for a role with no dataset yet - e.g.
    `CONTINUITY_CHECKER`, which has no LLM call to benchmark at all (see
    module docstring)."""
    return list(_CASES_BY_ROLE.get(role, []))


def available_roles() -> list[ModelRole]:
    return list(_CASES_BY_ROLE.keys())
