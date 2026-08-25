"""Video production workflow contract (Module 08).

Mirrors `domain/storyboard.py`'s pattern exactly: `ShotVideoProduction` is a
lightweight per-shot workflow record (status + approved-take pointer);
individual video takes stay plain `Asset` rows (Module 04, `type=video`,
`take_number`) - no duplicated asset-like entity.

`extracted_last_frame_asset_id` is set only once the approved take's actual
final frame has been extracted (see research/PRODUCTION_STACK_2026.md
"Previous-frame continuity") - it becomes the next shot's first-frame input
when both shots share a `continuity_group`.
"""

from pydantic import BaseModel


class ShotVideoProduction(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    shot_number: int
    continuity_group: str | None = None
    status: str = "draft"  # draft | approved
    approved_take_asset_id: str | None = None
    extracted_last_frame_asset_id: str | None = None
    # MODULE-045 - see domain/storyboard.py's identical fields.
    auto_retake_attempts: int = 0
    escalated: bool = False
