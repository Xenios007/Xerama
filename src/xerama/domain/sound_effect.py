"""Sound effect cue domain contract (MODULE-038).

"Represent and source story-relevant SFX/ambience as timeline assets" -
structured production data instead of manual post-production notes.
"""

from pydantic import BaseModel, Field

from xerama.domain.rights import RightsMetadata


class SoundEffectCue(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    shot_number: int | None = None
    # What in the shot/micro-beat triggered this cue, e.g. "door slams" -
    # kept even after an asset is linked, as the human-readable reason
    # this cue exists.
    description: str = ""
    start_seconds: float
    end_seconds: float
    gain_db: float = 0.0
    asset_id: str | None = None
    rights: RightsMetadata = Field(default_factory=RightsMetadata)
    status: str = "draft"  # draft | approved
