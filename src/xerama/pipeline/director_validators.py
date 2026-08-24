"""Deterministic Director-level validation passes (Module 03).

Distinct from `pipeline/validators.py` (story-level retention/continuity):
these checks are about shot-list *production readiness* - vertical
composition, dialogue coverage, and continuity-group structure - not
narrative canon. They never BLOCK canon commit; they are informational QC
for the Director/Media Engine, matching ADR-018 (pass/warn/block + reasons)
applied to production rather than story quality.
"""

from collections import defaultdict

from xerama.domain.enums import QCStatus
from xerama.domain.episode import EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan, Shot


class DirectorValidator:
    def check_vertical_composition(self, plan: EpisodeShotPlan) -> QCResult:
        """See ADR-015 - 9:16 needs deliberate composition, not just an
        aspect-ratio setting."""

        reasons: list[str] = []
        for scene in plan.scenes:
            for shot in scene.shots:
                if not shot.camera.shot_size.strip():
                    reasons.append(
                        f"scene {scene.scene_number} shot {shot.shot_number} has no camera.shot_size"
                    )
                if not shot.visual.composition.strip():
                    reasons.append(
                        f"scene {scene.scene_number} shot {shot.shot_number} has no visual.composition"
                    )
                shot_size = shot.camera.shot_size.lower()
                if len(shot.character_ids) >= 3 and "wide" not in shot_size and "full" not in shot_size:
                    reasons.append(
                        f"scene {scene.scene_number} shot {shot.shot_number} frames "
                        f"{len(shot.character_ids)} characters without a wide/full shot_size "
                        "- vertical crowding risk"
                    )

        status = QCStatus.WARN if reasons else QCStatus.PASS
        score = max(0.0, 10.0 - len(reasons))
        return QCResult(
            gate="director_vertical",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation="Set an explicit shot_size/composition for the flagged shots." if reasons else "",
        )

    def check_dialogue_coverage(self, script: EpisodeScript, plan: EpisodeShotPlan) -> QCResult:
        """See research/WIND_COMIC_DEEP_DIVE.md section 7 - a multi-speaker
        scene needs single/reaction coverage, not one continuous two-shot."""

        reasons: list[str] = []
        plan_scenes = {scene.scene_number: scene for scene in plan.scenes}
        for script_scene in script.scenes:
            speakers = {line.character_id for line in script_scene.dialogue}
            if len(speakers) < 2:
                continue
            plan_scene = plan_scenes.get(script_scene.scene_number)
            if plan_scene is None or not plan_scene.shots:
                reasons.append(
                    f"scene {script_scene.scene_number} has {len(speakers)}-speaker dialogue but no shots planned"
                )
                continue
            has_single_or_reaction_shot = any(len(shot.character_ids) <= 1 for shot in plan_scene.shots)
            if not has_single_or_reaction_shot:
                reasons.append(
                    f"scene {script_scene.scene_number} has {len(speakers)}-speaker dialogue but every "
                    "shot keeps all speakers on screen together - no single/reaction coverage"
                )

        status = QCStatus.WARN if reasons else QCStatus.PASS
        score = max(0.0, 10.0 - 3 * len(reasons))
        return QCResult(
            gate="director_dialogue_coverage",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Add single/reaction shots for the flagged multi-speaker scenes." if reasons else ""
            ),
        )

    def check_continuity_grouping(self, plan: EpisodeShotPlan) -> QCResult:
        """See ADR-017 - continuity groups must be a contiguous shot run so
        the scheduler can generate them sequentially and chain last->first
        frames."""

        reasons: list[str] = []
        for scene in plan.scenes:
            shots_sorted = sorted(scene.shots, key=lambda s: s.shot_number)
            group_positions: dict[str, list[int]] = defaultdict(list)
            for index, shot in enumerate(shots_sorted):
                if shot.continuity_group:
                    group_positions[shot.continuity_group].append(index)

            for group, positions in group_positions.items():
                contiguous = positions == list(range(positions[0], positions[0] + len(positions)))
                if not contiguous:
                    reasons.append(
                        f"scene {scene.scene_number} continuity_group '{group}' is not a contiguous "
                        "shot run"
                    )
                    continue
                # Every shot but the last in the group should hand off its
                # final frame to the next one.
                group_shots = [shots_sorted[i] for i in positions]
                for shot in group_shots[:-1]:
                    if not shot.provider_requirements.last_frame_required:
                        reasons.append(
                            f"scene {scene.scene_number} shot {shot.shot_number} is mid continuity_group "
                            f"'{group}' but last_frame_required is false"
                        )

        status = QCStatus.BLOCK if any("not a contiguous" in r for r in reasons) else (
            QCStatus.WARN if reasons else QCStatus.PASS
        )
        score = 0.0 if status == QCStatus.BLOCK else max(0.0, 10.0 - 2 * len(reasons))
        return QCResult(
            gate="director_continuity_grouping",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Fix continuity_group assignment so grouped shots are contiguous and hand off frames."
                if reasons
                else ""
            ),
        )

    def check_scene_blocking(self, plan: EpisodeShotPlan) -> QCResult:
        """See MODULE-022 - validate multi-character blocking data
        integrity and screen-direction preservation across a
        continuity_group. Shots without a `blocking_plan` are skipped -
        the structured plan is optional, layered on top of free-text
        `blocking`."""

        reasons: list[str] = []
        for scene in plan.scenes:
            shots_sorted = sorted(scene.shots, key=lambda s: s.shot_number)
            for shot in shots_sorted:
                if shot.blocking_plan is None:
                    continue
                blocked_ids = {cb.character_id for cb in shot.blocking_plan.characters}
                missing = [cid for cid in shot.character_ids if cid not in blocked_ids]
                if missing:
                    reasons.append(
                        f"scene {scene.scene_number} shot {shot.shot_number} blocking_plan is missing "
                        f"CharacterBlock entries for {missing}"
                    )
                visible = [cb for cb in shot.blocking_plan.characters if cb.visible]
                for i, a in enumerate(visible):
                    for b in visible[i + 1 :]:
                        same_spot = a.position == b.position and a.depth == b.depth
                        documented = b.character_id in a.occluded_by or a.character_id in b.occluded_by
                        if same_spot and not documented:
                            reasons.append(
                                f"scene {scene.scene_number} shot {shot.shot_number}: "
                                f"{a.character_id} and {b.character_id} share position={a.position.value}/"
                                f"depth={a.depth.value} without a documented occlusion"
                            )

            by_group: dict[str, list[Shot]] = defaultdict(list)
            for shot in shots_sorted:
                if shot.continuity_group:
                    by_group[shot.continuity_group].append(shot)
            for group, shots_in_group in by_group.items():
                directions = {
                    s.blocking_plan.screen_direction
                    for s in shots_in_group
                    if s.blocking_plan and s.blocking_plan.screen_direction
                }
                if len(directions) > 1:
                    reasons.append(
                        f"scene {scene.scene_number} continuity_group '{group}' changes screen_direction "
                        f"across shots ({sorted(directions)}) without an explicit reset"
                    )

        missing_reasons = [r for r in reasons if "missing CharacterBlock" in r]
        status = QCStatus.BLOCK if missing_reasons else (QCStatus.WARN if reasons else QCStatus.PASS)
        score = 0.0 if status == QCStatus.BLOCK else max(0.0, 10.0 - 2 * len(reasons))
        return QCResult(
            gate="director_scene_blocking",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Add a CharacterBlock for every character in the shot and keep continuity-group "
                "screen_direction consistent."
                if reasons
                else ""
            ),
        )

    def check_motion_plan(self, plan: EpisodeShotPlan) -> QCResult:
        """See MODULE-033 - detect impossible or overloaded motion plans
        before generation. Provider capability differences for
        performance/subject reference are already handled by
        `ProviderRequirements`/`VideoProviderCapabilities`
        (`providers/video.py:matches_requirements`, Module 07/08) - nothing
        further needed here. "Keep dialogue performance linked to speaker/
        emotion" is satisfied by construction: `MicroBeat.character_id`
        ties every structured beat to a specific speaker."""

        reasons: list[str] = []
        for scene in plan.scenes:
            for shot in scene.shots:
                beats = sorted(shot.micro_beats, key=lambda b: b.start_seconds)
                for beat in beats:
                    if beat.start_seconds >= beat.end_seconds:
                        reasons.append(
                            f"scene {scene.scene_number} shot {shot.shot_number}: micro_beat has "
                            f"start_seconds >= end_seconds ({beat.start_seconds} >= {beat.end_seconds})"
                        )
                    elif beat.end_seconds > shot.duration_seconds:
                        reasons.append(
                            f"scene {scene.scene_number} shot {shot.shot_number}: micro_beat "
                            f"[{beat.start_seconds}-{beat.end_seconds}] extends past the shot's "
                            f"duration_seconds={shot.duration_seconds}"
                        )

                by_character: dict[str, list] = defaultdict(list)
                for beat in beats:
                    if beat.character_id:
                        by_character[beat.character_id].append(beat)
                for character_id, character_beats in by_character.items():
                    for prev, nxt in zip(character_beats, character_beats[1:]):
                        if prev.end_seconds > nxt.start_seconds:
                            reasons.append(
                                f"scene {scene.scene_number} shot {shot.shot_number}: {character_id} "
                                f"has overlapping micro_beats [{prev.start_seconds}-{prev.end_seconds}] "
                                f"and [{nxt.start_seconds}-{nxt.end_seconds}] - an impossible "
                                "simultaneous pose/expression/gaze"
                            )

                if beats and shot.duration_seconds > 0 and len(beats) / shot.duration_seconds > 1.0:
                    reasons.append(
                        f"scene {scene.scene_number} shot {shot.shot_number}: {len(beats)} "
                        f"micro_beats in {shot.duration_seconds}s is an overloaded motion plan "
                        "(>1 beat/second)"
                    )

        impossible = [
            r
            for r in reasons
            if "extends past" in r or "start_seconds >=" in r or "overlapping micro_beats" in r
        ]
        status = QCStatus.BLOCK if impossible else (QCStatus.WARN if reasons else QCStatus.PASS)
        score = 0.0 if status == QCStatus.BLOCK else max(0.0, 10.0 - 2 * len(reasons))
        return QCResult(
            gate="director_motion_plan",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Fix overlapping/out-of-bounds micro_beats or reduce beat density per shot."
                if reasons
                else ""
            ),
        )
