"""Subtitle track generation/export service (MODULE-039).

Deterministically derives one cue per dialogue shot from the approved shot
plan (`pipeline/subtitle_generation.py`), persists the whole track
idempotently (regeneration replaces, never accumulates), and exposes SRT
export + readability validation.
"""

from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.subtitle import SubtitleCue
from xerama.pipeline.subtitle_generation import cues_from_shot_plan, export_srt
from xerama.pipeline.subtitle_validators import SubtitleValidator
from xerama.repositories.interfaces import SubtitleCueRepository


class SubtitleService:
    def __init__(self, repo: SubtitleCueRepository, validator: SubtitleValidator | None = None) -> None:
        self._repo = repo
        self._validator = validator or SubtitleValidator()

    async def generate_track(
        self, episode_id: str, plan: EpisodeShotPlan, language: str = "en"
    ) -> list[SubtitleCue]:
        cues = cues_from_shot_plan(plan, language)
        return await self._repo.replace_track(episode_id, language, cues)

    async def list_by_episode(self, episode_id: str, language: str = "en") -> list[SubtitleCue]:
        return await self._repo.list_by_episode(episode_id, language)

    async def export_srt(self, episode_id: str, language: str = "en") -> str:
        cues = await self.list_by_episode(episode_id, language)
        return export_srt(cues)

    async def validate_readability(self, episode_id: str, language: str = "en") -> QCResult:
        cues = await self.list_by_episode(episode_id, language)
        return self._validator.check_readability(cues)
