"""Music cue planning service (MODULE-037).

"Plan and attach licensed/generated music cues without entangling story or
editor logic." A cue starts as `draft` planning metadata; linking an asset
is "library asset selection first" (a generation provider is optional and
not required to satisfy this module - none is wired up here); `approve_cue`
is the one gate that "prevents unlicensed/unknown provenance assets from
publish-ready state" - it refuses to approve a cue with no linked asset or
unknown/empty `rights.license_type`.
"""

from xerama.domain.music import MusicCue
from xerama.domain.rights import RightsMetadata
from xerama.repositories.interfaces import MusicCueRepository


class CueNotReadyError(ValueError):
    """Raised when a cue is asked to approve without a linked asset - the
    cue exists, it just isn't ready yet (distinct from "not found")."""


class MusicCueService:
    def __init__(self, repo: MusicCueRepository) -> None:
        self._repo = repo

    async def create_cue(
        self,
        episode_id: str,
        purpose: str,
        mood: str,
        start_seconds: float,
        end_seconds: float,
        ducking_db: float = 0.0,
        scene_number: int | None = None,
    ) -> MusicCue:
        return await self._repo.create(
            episode_id, purpose, mood, start_seconds, end_seconds, ducking_db, scene_number
        )

    async def get(self, cue_id: str) -> MusicCue:
        cue = await self._repo.get(cue_id)
        if cue is None:
            raise ValueError(f"music cue {cue_id} not found")
        return cue

    async def list_by_episode(self, episode_id: str) -> list[MusicCue]:
        return await self._repo.list_by_episode(episode_id)

    async def link_asset(self, cue_id: str, asset_id: str, rights: RightsMetadata) -> MusicCue:
        cue = await self.get(cue_id)
        cue.asset_id = asset_id
        cue.rights = rights
        cue.status = "draft"  # re-linking resets approval - never silently keep an approval current
        return await self._repo.update(cue)

    async def approve_cue(self, cue_id: str) -> MusicCue:
        cue = await self.get(cue_id)
        if cue.asset_id is None:
            raise CueNotReadyError(f"music cue {cue_id} has no linked asset")
        if not cue.rights.is_known:
            raise PermissionError(
                f"music cue {cue_id} has unknown/unlicensed rights - cannot reach publish-ready state"
            )
        cue.status = "approved"
        return await self._repo.update(cue)

    async def delete_cue(self, cue_id: str) -> None:
        await self._repo.delete(cue_id)
