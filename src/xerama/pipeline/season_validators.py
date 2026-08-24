"""Season/reveal-map validation heuristics (Module 01).

Deterministic, non-LLM checks - same philosophy as
`pipeline/validators.py` (ADR-018: pass/warn/block + reasons + repair
recommendation, not one opaque score). Guards against premature reveals,
forgotten setup/payoffs, repetitive cliffhangers and episodes that don't
advance the season - see modules/01_SEASON_REVEAL_ENGINE.md "Validation".
"""

from xerama.domain.character import CharacterCast
from xerama.domain.enums import QCStatus, ThreadStatus
from xerama.domain.quality import QCResult
from xerama.domain.season import SeasonPlan


class SeasonValidator:
    def validate(self, plan: SeasonPlan, cast: CharacterCast) -> QCResult:
        reasons: list[str] = []
        blocking = False
        warnings = 0

        # -- episode coverage ------------------------------------------------
        expected = set(range(1, plan.episode_count + 1))
        assigned = [a.episode_number for a in plan.episode_assignments]
        assigned_set = set(assigned)
        missing = sorted(expected - assigned_set)
        duplicates = sorted({n for n in assigned if assigned.count(n) > 1})
        extra = sorted(assigned_set - expected)
        if missing:
            blocking = True
            reasons.append(f"episode assignments missing for episodes {missing}")
        if duplicates:
            blocking = True
            reasons.append(f"duplicate episode assignments for episodes {duplicates}")
        if extra:
            blocking = True
            reasons.append(f"episode assignments reference out-of-range episodes {extra}")

        # -- reveal ordering ---------------------------------------------------
        mystery_by_id = {m.id: m for m in plan.mysteries}
        reveal_by_id = {r.id: r for r in plan.reveals}
        for reveal in plan.reveals:
            if not (1 <= reveal.planned_episode <= plan.episode_count):
                blocking = True
                reasons.append(f"reveal '{reveal.id}' is planned outside the season (episode {reveal.planned_episode})")
            if reveal.mystery_id is not None:
                mystery = mystery_by_id.get(reveal.mystery_id)
                if mystery is None:
                    blocking = True
                    reasons.append(f"reveal '{reveal.id}' references unknown mystery '{reveal.mystery_id}'")
                elif reveal.planned_episode < mystery.introduced_episode:
                    blocking = True
                    reasons.append(
                        f"reveal '{reveal.id}' is planned before its mystery '{mystery.id}' is introduced"
                    )
            for dep_id in reveal.depends_on:
                dep = reveal_by_id.get(dep_id)
                if dep is None:
                    blocking = True
                    reasons.append(f"reveal '{reveal.id}' depends on unknown reveal '{dep_id}'")
                elif dep.planned_episode > reveal.planned_episode:
                    blocking = True
                    reasons.append(
                        f"reveal '{reveal.id}' is planned before its prerequisite reveal '{dep_id}' (premature reveal)"
                    )

        # -- setup-before-payoff -------------------------------------------
        for promise in plan.promises:
            if not (1 <= promise.setup_episode <= plan.episode_count):
                blocking = True
                reasons.append(f"promise '{promise.id}' is set up outside the season")
            if promise.payoff_episode is not None:
                if promise.payoff_episode > plan.episode_count:
                    blocking = True
                    reasons.append(f"promise '{promise.id}' pays off outside the season")
                elif promise.payoff_episode <= promise.setup_episode:
                    blocking = True
                    reasons.append(f"promise '{promise.id}' pays off before/at its own setup episode")
            if promise.status == ThreadStatus.RESOLVED and promise.payoff_episode is None:
                blocking = True
                reasons.append(f"promise '{promise.id}' is marked resolved but has no payoff_episode")

        for mystery in plan.mysteries:
            if mystery.resolution_episode is not None and mystery.resolution_episode > plan.episode_count:
                blocking = True
                reasons.append(f"mystery '{mystery.id}' resolves outside the season")
            if mystery.status == ThreadStatus.RESOLVED and mystery.resolution_episode is None:
                blocking = True
                reasons.append(f"mystery '{mystery.id}' is marked resolved but has no resolution_episode")

        # -- unresolved end-state (deliberate vs. forgotten) -----------------
        open_mysteries = [m for m in plan.mysteries if m.status != ThreadStatus.RESOLVED]
        open_promises = [p for p in plan.promises if p.status != ThreadStatus.RESOLVED]
        if plan.mysteries or plan.promises:
            if not open_mysteries and not open_promises:
                warnings += 1
                reasons.append(
                    "every mystery/promise resolves within the season - no continuation hook remains "
                    "(fine for a series finale, otherwise leave at least one thread open)"
                )

        # -- escalation progression -----------------------------------------
        levels = sorted(plan.escalation_milestones, key=lambda m: m.episode_number)
        if len(levels) >= 2 and levels[-1].escalation_level <= levels[0].escalation_level:
            warnings += 1
            reasons.append("escalation does not trend upward across the season")

        assignments_sorted = sorted(plan.episode_assignments, key=lambda a: a.episode_number)
        if len(assignments_sorted) >= 2 and (
            assignments_sorted[-1].escalation_level <= assignments_sorted[0].escalation_level
        ):
            warnings += 1
            reasons.append("final episode's escalation_level is not higher than the first episode's")

        # -- character-arc coverage ------------------------------------------
        milestone_character_ids = {m.character_id for m in plan.character_arc_milestones}
        missing_arcs = [c.id for c in cast.characters if c.id not in milestone_character_ids]
        if missing_arcs:
            warnings += 1
            reasons.append(f"characters with no season arc milestone: {missing_arcs}")

        # -- duplicate/repetitive beats ---------------------------------------
        prev_type = None
        for assignment in assignments_sorted:
            if assignment.cliffhanger_type is not None and assignment.cliffhanger_type == prev_type:
                warnings += 1
                reasons.append(
                    f"episode {assignment.episode_number} repeats the previous episode's cliffhanger type "
                    f"'{assignment.cliffhanger_type.value}'"
                )
            if assignment.cliffhanger_type is not None:
                prev_type = assignment.cliffhanger_type

        no_progress = [
            a.episode_number
            for a in assignments_sorted
            if not a.reveals and not a.promises_setup and not a.promises_paid_off and not a.character_milestones
        ]
        if no_progress:
            warnings += 1
            reasons.append(f"episodes with no reveal/promise/character-arc progress: {no_progress}")

        if blocking:
            status = QCStatus.BLOCK
        elif warnings:
            status = QCStatus.WARN
        else:
            status = QCStatus.PASS

        total_checks = 7
        penalized = min(total_checks, warnings + (total_checks if blocking else 0))
        score = 0.0 if blocking else max(0.0, min(10.0, ((total_checks - penalized) / total_checks) * 10))

        return QCResult(
            gate="season",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Regenerate the season plan fixing episode coverage/reveal ordering/setup-payoff errors."
                if blocking
                else ("Address the warnings above before approving this season plan." if warnings else "")
            ),
        )
