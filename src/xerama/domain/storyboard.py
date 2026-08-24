"""Storyboard/keyframe workflow contract (Module 06).

A `Storyboard` is the per-shot production record for the still-image stage:
"approved shot -> rough storyboard/layout -> compiled references -> final
keyframe -> QC state -> accept/retry." It does not hold image bytes or even
duplicate asset metadata - individual keyframe attempts (takes) are plain
`Asset` rows (type=image, ownership.scene_number/shot_number, take_number)
from Module 04; a `Storyboard` just tracks workflow status and which take
was approved.
"""

from pydantic import BaseModel


class Storyboard(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    shot_number: int
    status: str = "draft"  # draft | approved
    layout_description: str = ""
    approved_keyframe_asset_id: str | None = None
