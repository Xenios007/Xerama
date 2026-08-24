"""Deterministic retention and continuity validators.

These are pure-Python heuristics, not LLM calls - see docs/ARCHITECTURE.md
"Closed-loop quality" and ADR-018 (pass/warn/block, not one opaque score).
They are explicitly initial heuristics to complement (not replace) an LLM
critic later - see research/WIND_COMIC_DEEP_DIVE.md section 6 and
research/CODING_READINESS_CHECKLIST.md.
"""

from xerama.domain.character import CharacterCast
from xerama.domain.enums import CliffhangerType, QCStatus
from xerama.domain.episode import EpisodeOutline, EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan


class RetentionValidator:
    """Hook/pacing/cliffhanger/runtime heuristics. See docs/STORY_FORMULA.md."""

    def validate(
        self,
        outline: EpisodeOutline,
        script: EpisodeScript,
        shot_plan: EpisodeShotPlan | None = None,
        recent_cliffhanger_types: list[CliffhangerType] | None = None,
    ) -> QCResult:
        reasons: list[str] = []
        blocking = False
        warnings = 0
        checks = 0

        checks += 1
        if len(outline.opening_hook.strip()) < 10:
            blocking = True
            reasons.append("opening_hook is missing or too short to create curiosity")

        checks += 1
        if not outline.cliffhanger.event.strip():
            blocking = True
            reasons.append("cliffhanger event is empty")

        checks += 1
        recent_cliffhanger_types = recent_cliffhanger_types or []
        if recent_cliffhanger_types and outline.cliffhanger.type == recent_cliffhanger_types[-1]:
            warnings += 1
            reasons.append(
                f"cliffhanger type '{outline.cliffhanger.type.value}' repeats the previous episode"
            )

        checks += 1
        if not outline.escalation:
            warnings += 1
            reasons.append("no escalation beats defined - conflict may read as flat")

        checks += 1
        if not outline.turn.strip():
            warnings += 1
            reasons.append("no turn/reversal defined for this episode")

        checks += 1
        empty_scenes = [s.scene_number for s in script.scenes if not s.action.strip() and not s.dialogue]
        if empty_scenes:
            warnings += 1
            reasons.append(f"scenes with no action or dialogue: {empty_scenes}")

        if shot_plan is not None:
            checks += 1
            total_duration = sum(shot.duration_seconds for scene in shot_plan.scenes for shot in scene.shots)
            target = outline.duration_target_seconds
            if target > 0 and abs(total_duration - target) / target > 0.3:
                warnings += 1
                reasons.append(
                    f"planned shot duration {total_duration:.0f}s deviates >30% from target {target}s"
                )

        if blocking:
            status = QCStatus.BLOCK
        elif warnings:
            status = QCStatus.WARN
        else:
            status = QCStatus.PASS

        passed = checks - warnings - (1 if blocking else 0)
        score = max(0.0, min(10.0, (passed / checks) * 10)) if checks else 0.0

        return QCResult(
            gate="retention",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Strengthen the opening hook and ensure a real cliffhanger before rescoring."
                if blocking
                else ("Address the warnings above before treating this episode as approved." if warnings else "")
            ),
        )


class ContinuityValidator:
    """Referential-integrity heuristics against canonical cast/state.

    V1 scope: verifies every character referenced by the script/shot plan
    exists in the approved cast, and that shot-plan locations trace back to
    script scenes. Deeper contradiction detection (knowledge/timeline/props)
    is deferred - see docs/DATA_MODEL.md "Canon Commit Rule".
    """

    def validate(
        self,
        cast: CharacterCast,
        script: EpisodeScript,
        shot_plan: EpisodeShotPlan | None = None,
    ) -> QCResult:
        reasons: list[str] = []
        known_ids = {c.id for c in cast.characters}
        blocking = False

        for scene in script.scenes:
            unknown = [cid for cid in scene.characters if cid not in known_ids]
            if unknown:
                blocking = True
                reasons.append(f"script scene {scene.scene_number} references unknown character(s) {unknown}")
            for line in scene.dialogue:
                if line.character_id not in known_ids:
                    blocking = True
                    reasons.append(
                        f"script scene {scene.scene_number} has dialogue from unknown character '{line.character_id}'"
                    )

        known_locations = {scene.location for scene in script.scenes}
        if shot_plan is not None:
            for scene in shot_plan.scenes:
                unknown = [cid for shot in scene.shots for cid in shot.character_ids if cid not in known_ids]
                if unknown:
                    blocking = True
                    reasons.append(f"shot plan scene {scene.scene_number} references unknown character(s) {unknown}")
                if scene.location and scene.location not in known_locations:
                    reasons.append(
                        f"shot plan scene {scene.scene_number} location '{scene.location}' has no matching script scene"
                    )

        status = QCStatus.BLOCK if blocking else (QCStatus.WARN if reasons else QCStatus.PASS)
        score = 0.0 if blocking else (6.0 if reasons else 10.0)

        return QCResult(
            gate="continuity",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Regenerate the offending scene/shot referencing only approved cast members."
                if blocking
                else ""
            ),
        )
