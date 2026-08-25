"""Automatic-retake escalation policy (MODULE-045).

Decides, for a take that just failed its MODULE-044 QC gate, whether an
automatic repair should be attempted (and which kind) or whether the
failure should escalate to human review - "escalate repeated failure to
human review rather than loop forever." Pure policy: this service does not
call any provider or mutate any generation request itself -
`StoryboardService`/`VideoProductionService`/`AudioProductionService` use
the returned `RepairPlan` to decide how to adjust their next `generate_*`
call, and are the ones that persist the per-production attempt counter
via their repository's `record_retake_attempt`.
"""

from dataclasses import dataclass, field

from xerama.domain.enums import QCStatus, RepairAction
from xerama.domain.media_qc import MediaQCAttempt
from xerama.pipeline.retake_policy import classify_repair_action

# "Enforce retry/cost limits" - after this many automatic repair attempts
# on the same production record, stop retrying and escalate. A module-level
# constant, same override-later-if-needed precedent as every other
# threshold in this codebase (e.g. IDENTITY_SIMILARITY_PASS_THRESHOLD).
MAX_AUTO_RETAKE_ATTEMPTS = 3


@dataclass
class RepairPlan:
    action: RepairAction
    reasons: list[str] = field(default_factory=list)


class AutomaticRetakeService:
    def plan_repair(self, attempts: list[MediaQCAttempt], prior_attempt_count: int) -> RepairPlan:
        blocked_reasons = [r for a in attempts if a.status == QCStatus.BLOCK for r in a.reasons]
        if prior_attempt_count >= MAX_AUTO_RETAKE_ATTEMPTS:
            return RepairPlan(action=RepairAction.ESCALATE, reasons=blocked_reasons)
        return RepairPlan(action=classify_repair_action(attempts), reasons=blocked_reasons)
