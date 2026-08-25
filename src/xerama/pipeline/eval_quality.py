"""Deterministic quality rubrics for eval harness output (MODULE-072).

Same "deterministic keyword/threshold heuristics preferred over LLM
calls" choice as MODULE-063's cliffhanger classification and MODULE-065's
repair-action mapping - a rubric score must be cheap, instant, and
auditable (every check is inspectable, unlike an LLM-as-judge score),
not another opaque AI call to benchmark AI calls with.

Each function returns a `(score, reasons)` pair: `score` on the same
0-10 scale as `MediaQCAttempt`/`JudgeCriteria` elsewhere in this
codebase, `reasons` a plain-English checklist result (which specific
checks passed/failed) - never a single unexplained number, matching
ADR-018's "never one opaque score" discipline applied here to eval
output instead of QC output.
"""

from xerama.domain.episode import EpisodeScript
from xerama.domain.story import ConceptCandidate, JudgeResult
from xerama.eval.datasets import EvalCase


def _ratio_score(passed: int, total: int) -> float:
    return round(10.0 * passed / total, 2) if total else 0.0


def score_concept_candidate(candidate: ConceptCandidate, case: EvalCase) -> tuple[float, list[str]]:
    checks: list[tuple[bool, str]] = [
        (bool(candidate.logline.strip()), "logline is non-empty"),
        (bool(candidate.premise.strip()), "premise is non-empty"),
        (bool(candidate.opening_hook.strip()), "opening_hook is non-empty"),
        (bool(candidate.central_conflict.strip()), "central_conflict is non-empty"),
        (bool(candidate.central_secret.strip()), "central_secret is non-empty"),
        (len(candidate.genre) > 0, "genre is non-empty"),
        (bool(candidate.protagonist.name.strip()), "protagonist.name is non-empty"),
        (bool(candidate.protagonist.desire.strip()), "protagonist.desire is non-empty"),
        (bool(candidate.protagonist.flaw.strip()), "protagonist.flaw is non-empty"),
        (len(candidate.major_reversals) > 0, "at least one major_reversal"),
    ]
    passed = [reason for ok, reason in checks if ok]
    failed = [f"MISSING: {reason}" for ok, reason in checks if not ok]
    return _ratio_score(len(passed), len(checks)), passed + failed


def score_judge_result(result: JudgeResult, case: EvalCase) -> tuple[float, list[str]]:
    criteria_values = result.criteria.model_dump().values()
    checks: list[tuple[bool, str]] = [
        (bool(result.reason.strip()) and len(result.reason.strip()) > 10, "reason is a real explanation"),
        (all(0 <= v <= 10 for v in criteria_values), "every criteria score is in [0, 10]"),
        (result.candidate_a.score != result.candidate_b.score or result.decision.value == "MERGE",
         "scores agree with a non-MERGE decision, or the decision is MERGE"),
    ]
    if result.decision.value == "MERGE":
        checks.append(
            (
                bool(
                    result.merge_instructions.take_from_a
                    or result.merge_instructions.take_from_b
                    or result.merge_instructions.requirements
                ),
                "MERGE decision includes actual merge_instructions",
            )
        )
    passed = [reason for ok, reason in checks if ok]
    failed = [f"MISSING: {reason}" for ok, reason in checks if not ok]
    return _ratio_score(len(passed), len(checks)), passed + failed


def score_episode_script(script: EpisodeScript, case: EvalCase) -> tuple[float, list[str]]:
    min_scenes = case.expectations.get("min_scenes", 1)
    target_duration = case.expectations.get("target_duration_seconds")

    checks: list[tuple[bool, str]] = [
        (len(script.scenes) >= min_scenes, f"at least {min_scenes} scene(s)"),
        (all(s.action.strip() for s in script.scenes), "every scene has non-empty action"),
        (all(len(s.dialogue) >= 1 for s in script.scenes), "every scene has at least one dialogue line"),
    ]
    if target_duration is not None:
        # Within 50% of target - a loose tolerance since exact runtime
        # pacing is a downstream (shot-planning) concern, not something
        # a script-writing model call should be penalized hard for.
        tolerance = target_duration * 0.5
        within = abs(script.estimated_duration_seconds - target_duration) <= tolerance
        checks.append((within, f"estimated_duration_seconds within 50% of {target_duration}s target"))
    passed = [reason for ok, reason in checks if ok]
    failed = [f"MISSING: {reason}" for ok, reason in checks if not ok]
    return _ratio_score(len(passed), len(checks)), passed + failed
