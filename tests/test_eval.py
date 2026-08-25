from xerama.domain.enums import JudgeDecision, ModelRole
from xerama.domain.episode import EpisodeScript, ScriptScene
from xerama.domain.eval import EvalRunResult
from xerama.domain.story import (
    CandidateScore,
    ConceptCandidate,
    JudgeCriteria,
    JudgeResult,
    MergeInstructions,
    Protagonist,
)
from xerama.eval.datasets import (
    CONCEPT_GENERATOR_CASES,
    EPISODE_WRITER_CASES,
    JUDGE_CASES,
    EvalCase,
    available_roles,
    cases_for_role,
)
from xerama.pipeline.eval_aggregation import summarize_by_role
from xerama.pipeline.eval_quality import score_concept_candidate, score_episode_script, score_judge_result

import fixtures as fx


# --- dataset (MODULE-072) -----------------------------------------------


def test_cases_for_role_returns_the_dataset_for_a_covered_role() -> None:
    assert cases_for_role(ModelRole.JUDGE) == JUDGE_CASES


def test_cases_for_role_returns_empty_for_an_uncovered_role() -> None:
    """CONTINUITY_CHECKER has no LLM call in this codebase to benchmark
    - see eval/datasets.py's module docstring."""
    assert cases_for_role(ModelRole.CONTINUITY_CHECKER) == []


def test_available_roles_matches_the_non_empty_datasets() -> None:
    roles = available_roles()
    assert ModelRole.CONCEPT_GENERATOR_A in roles
    assert ModelRole.JUDGE in roles
    assert ModelRole.EPISODE_WRITER in roles
    assert ModelRole.CONTINUITY_CHECKER not in roles


def test_every_dataset_case_has_a_unique_id() -> None:
    all_cases = CONCEPT_GENERATOR_CASES + JUDGE_CASES + EPISODE_WRITER_CASES
    ids = [c.id for c in all_cases]
    assert len(ids) == len(set(ids))


# --- quality rubrics -----------------------------------------------------


def _concept_case() -> EvalCase:
    return CONCEPT_GENERATOR_CASES[0]


def test_score_concept_candidate_scores_a_complete_candidate_at_the_top() -> None:
    candidate = ConceptCandidate(**fx.concept("A"))
    score, reasons = score_concept_candidate(candidate, _concept_case())
    assert score == 10.0
    assert not any(r.startswith("MISSING") for r in reasons)


def test_score_concept_candidate_penalizes_missing_fields() -> None:
    data = fx.concept("A")
    data["logline"] = ""
    data["major_reversals"] = []
    candidate = ConceptCandidate(**data)
    score, reasons = score_concept_candidate(candidate, _concept_case())
    assert score < 10.0
    assert any("logline" in r for r in reasons if r.startswith("MISSING"))
    assert any("reversal" in r for r in reasons if r.startswith("MISSING"))


def _judge_case() -> EvalCase:
    return JUDGE_CASES[0]


def test_score_judge_result_scores_a_well_formed_decision_at_the_top() -> None:
    result = JudgeResult(**fx.judge_result("A"))
    score, reasons = score_judge_result(result, _judge_case())
    assert score == 10.0
    assert not any(r.startswith("MISSING") for r in reasons)


def test_score_judge_result_penalizes_an_unexplained_decision() -> None:
    data = fx.judge_result("A")
    data["reason"] = "ok"
    result = JudgeResult(**data)
    score, reasons = score_judge_result(result, _judge_case())
    assert score < 10.0


def test_score_judge_result_requires_merge_instructions_for_a_merge_decision() -> None:
    result = JudgeResult(
        decision=JudgeDecision.MERGE,
        candidate_a=CandidateScore(score=7, strengths=[], weaknesses=[]),
        candidate_b=CandidateScore(score=7, strengths=[], weaknesses=[]),
        criteria=JudgeCriteria(
            hook=7, emotional_intensity=7, conflict=7, originality=7, serial_potential=7,
            reversal_potential=7, cliffhanger_potential=7, production_feasibility=7,
            character_potential=7,
        ),
        reason="Both candidates have real strengths worth combining.",
        merge_instructions=MergeInstructions(),  # empty - nothing to actually merge
    )
    score, reasons = score_judge_result(result, _judge_case())
    assert any("merge_instructions" in r for r in reasons if r.startswith("MISSING"))


def _script_case() -> EvalCase:
    return EPISODE_WRITER_CASES[0]  # target_duration_seconds=75, min_scenes=2


def test_score_episode_script_scores_a_well_formed_script_at_the_top() -> None:
    script = EpisodeScript(
        episode_number=1,
        title="Ep 1",
        scenes=[
            ScriptScene(
                scene_number=1, location="apt", time_of_day="night", characters=["C1"],
                action="Mara reads the letter.",
                dialogue=[{"character_id": "C1", "character_name": "Mara", "line": "No."}],
            ),
            ScriptScene(
                scene_number=2, location="street", time_of_day="night", characters=["C1"],
                action="Mara runs.",
                dialogue=[{"character_id": "C1", "character_name": "Mara", "line": "Wait!"}],
            ),
        ],
        estimated_duration_seconds=75.0,
    )
    score, reasons = score_episode_script(script, _script_case())
    assert score == 10.0
    assert not any(r.startswith("MISSING") for r in reasons)


def test_score_episode_script_penalizes_too_few_scenes() -> None:
    script = EpisodeScript(
        episode_number=1,
        title="Ep 1",
        scenes=[
            ScriptScene(
                scene_number=1, location="apt", time_of_day="night", characters=["C1"],
                action="Mara reads the letter.",
                dialogue=[{"character_id": "C1", "character_name": "Mara", "line": "No."}],
            ),
        ],
        estimated_duration_seconds=75.0,
    )
    score, reasons = score_episode_script(script, _script_case())
    assert score < 10.0
    assert any("scene" in r for r in reasons if r.startswith("MISSING"))


def test_score_episode_script_penalizes_runtime_far_from_target() -> None:
    script = EpisodeScript(
        episode_number=1,
        title="Ep 1",
        scenes=[
            ScriptScene(
                scene_number=1, location="apt", time_of_day="night", characters=["C1"],
                action="a", dialogue=[{"character_id": "C1", "character_name": "Mara", "line": "hi"}],
            ),
            ScriptScene(
                scene_number=2, location="apt", time_of_day="night", characters=["C1"],
                action="b", dialogue=[{"character_id": "C1", "character_name": "Mara", "line": "hi"}],
            ),
        ],
        estimated_duration_seconds=500.0,  # way past the 75s target
    )
    score, reasons = score_episode_script(script, _script_case())
    assert any("duration" in r for r in reasons if r.startswith("MISSING"))


# --- aggregation -----------------------------------------------------------


def _result(**overrides) -> EvalRunResult:
    fields = dict(
        id="R1", case_id="c1", role=ModelRole.JUDGE, dataset_version="v1",
        provider="openrouter", model="m1", schema_valid=True, quality_score=8.0, latency_ms=100.0,
    )
    fields.update(overrides)
    return EvalRunResult(**fields)


def test_summarize_by_role_groups_by_role_provider_and_model() -> None:
    results = [
        _result(id="R1", role=ModelRole.JUDGE, model="m1"),
        _result(id="R2", role=ModelRole.JUDGE, model="m2"),
        _result(id="R3", role=ModelRole.EPISODE_WRITER, model="m1"),
    ]
    benchmarks = summarize_by_role(results)
    keys = {(b.role, b.model) for b in benchmarks}
    assert keys == {
        (ModelRole.JUDGE, "m1"), (ModelRole.JUDGE, "m2"), (ModelRole.EPISODE_WRITER, "m1")
    }


def test_summarize_by_role_never_averages_across_roles() -> None:
    """"Compare models by logical role, not one global winner" - same
    model, two roles, must stay two separate rows."""
    results = [
        _result(id="R1", role=ModelRole.JUDGE, model="m1", quality_score=9.0),
        _result(id="R2", role=ModelRole.EPISODE_WRITER, model="m1", quality_score=3.0),
    ]
    benchmarks = summarize_by_role(results)
    assert len(benchmarks) == 2
    judge_row = next(b for b in benchmarks if b.role == ModelRole.JUDGE)
    writer_row = next(b for b in benchmarks if b.role == ModelRole.EPISODE_WRITER)
    assert judge_row.avg_quality_score == 9.0
    assert writer_row.avg_quality_score == 3.0


def test_summarize_by_role_computes_schema_success_rate() -> None:
    results = [
        _result(id="R1", schema_valid=True, quality_score=8.0),
        _result(id="R2", schema_valid=False, quality_score=None),
    ]
    benchmarks = summarize_by_role(results)
    assert len(benchmarks) == 1
    assert benchmarks[0].schema_success_rate == 0.5
    assert benchmarks[0].sample_count == 2


def test_summarize_by_role_never_fabricates_a_quality_score_when_all_invalid() -> None:
    results = [_result(id="R1", schema_valid=False, quality_score=None)]
    benchmarks = summarize_by_role(results)
    assert benchmarks[0].avg_quality_score is None
