"""Music cue domain contract (MODULE-037).

"Plan and attach licensed/generated music cues without entangling story or
editor logic." A cue is planning metadata - purpose/mood/timing/ducking -
plus a pointer to the actual audio `Asset` (Module 04) once one is
selected/generated; the cue itself carries no audio bytes.
"""

from pydantic import BaseModel, Field

from xerama.domain.rights import RightsMetadata


class MusicCue(BaseModel):
    id: str
    episode_id: str
    # None means the cue spans the whole episode rather than one scene.
    scene_number: int | None = None
    purpose: str = ""  # e.g. "tension build", "emotional low point"
    mood: str = ""
    start_seconds: float
    end_seconds: float
    ducking_db: float = 0.0  # how much to duck under dialogue (negative dB)
    asset_id: str | None = None
    rights: RightsMetadata = Field(default_factory=RightsMetadata)
    status: str = "draft"  # draft | approved
