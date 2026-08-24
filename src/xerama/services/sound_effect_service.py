"""Sound effect cue service (MODULE-038).

Same shape as `MusicCueService` (draft -> link a library asset -> approve,
with `approve_cue` refusing unknown/unlicensed rights), plus
`derive_candidates_for_shot` which persists the deterministic keyword-based
candidates from `pipeline/sfx_derivation.py` as draft cues ready for a
human/editor to link an asset to and approve.
"""

from xerama.domain.rights import RightsMetadata
from xerama.domain.scene import Shot
from xerama.domain.sound_effect import SoundEffectCue
from xerama.pipeline.sfx_derivation import derive_sfx_candidates
from xerama.repositories.interfaces import SoundEffectCueRepository


class CueNotReadyError(ValueError):
    """Raised when a cue is asked to approve without a linked asset - the
    cue exists, it just isn't ready yet (distinct from "not found")."""


class SoundEffectCueService:
    def __init__(self, repo: SoundEffectCueRepository) -> None:
        self._repo = repo

    async def create_cue(
        self,
        episode_id: str,
        scene_number: int,
        description: str,
        start_seconds: float,
        end_seconds: float,
        shot_number: int | None = None,
        gain_db: float = 0.0,
    ) -> SoundEffectCue:
        return await self._repo.create(
            episode_id, scene_number, description, start_seconds, end_seconds, shot_number, gain_db
        )

    async def derive_candidates_for_shot(
        self, episode_id: str, scene_number: int, shot: Shot
    ) -> list[SoundEffectCue]:
        return [
            await self.create_cue(
                episode_id, scene_number, description, start_seconds, end_seconds, shot.shot_number
            )
            for description, start_seconds, end_seconds in derive_sfx_candidates(shot)
        ]

    async def get(self, cue_id: str) -> SoundEffectCue:
        cue = await self._repo.get(cue_id)
        if cue is None:
            raise ValueError(f"sound effect cue {cue_id} not found")
        return cue

    async def list_by_episode(self, episode_id: str) -> list[SoundEffectCue]:
        return await self._repo.list_by_episode(episode_id)

    async def link_asset(self, cue_id: str, asset_id: str, rights: RightsMetadata) -> SoundEffectCue:
        cue = await self.get(cue_id)
        cue.asset_id = asset_id
        cue.rights = rights
        cue.status = "draft"
        return await self._repo.update(cue)

    async def approve_cue(self, cue_id: str) -> SoundEffectCue:
        cue = await self.get(cue_id)
        if cue.asset_id is None:
            raise CueNotReadyError(f"sound effect cue {cue_id} has no linked asset")
        if not cue.rights.is_known:
            raise PermissionError(
                f"sound effect cue {cue_id} has unknown/unlicensed rights - cannot reach publish-ready state"
            )
        cue.status = "approved"
        return await self._repo.update(cue)

    async def delete_cue(self, cue_id: str) -> None:
        await self._repo.delete(cue_id)
