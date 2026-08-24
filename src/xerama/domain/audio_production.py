"""Dialogue/audio production workflow contract (MODULE-035).

Mirrors `domain/storyboard.py`/`domain/video_production.py`'s pattern: a
lightweight per-shot workflow record (status + approved-take pointer);
individual audio takes stay plain `Asset` rows (`type=audio`,
`take_number`) - no duplicated asset-like entity.
"""

from pydantic import BaseModel

from xerama.domain.enums import AudioMode


class ShotAudioProduction(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    shot_number: int
    # Copied from Shot.audio_mode at creation time (native/tts_lipsync/
    # hybrid - Module 03) so the production record always reflects what
    # the Director actually specified for this shot.
    audio_mode: AudioMode = AudioMode.NATIVE
    status: str = "draft"  # draft | approved
    approved_take_asset_id: str | None = None
