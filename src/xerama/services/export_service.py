"""Vertical export service (MODULE-048).

Reuses `EpisodeAssemblyService.render_episode` (MODULE-046) rather than a
second encode pipeline - an export *is* a render, parameterized by an
`ExportProfile`'s `OutputSpec`, with an `MediaInspector`-backed validation
report layered on top.
"""

from xerama.domain.asset import Asset
from xerama.domain.episode_render import EpisodeRender
from xerama.domain.export import VERTICAL_1080_1920, ExportProfile
from xerama.domain.quality import QCResult
from xerama.pipeline.export_validation import validate_export
from xerama.providers.media_inspector import MediaInspector
from xerama.repositories.interfaces import SubtitleCueRepository
from xerama.services.assembly_service import EpisodeAssemblyService
from xerama.services.asset_service import AssetService


class VerticalExportService:
    def __init__(
        self,
        assembly_service: EpisodeAssemblyService,
        asset_service: AssetService,
        subtitle_repo: SubtitleCueRepository,
        inspector: MediaInspector,
    ) -> None:
        self._assembly_service = assembly_service
        self._asset_service = asset_service
        self._subtitle_repo = subtitle_repo
        self._inspector = inspector

    async def export_episode(
        self,
        episode_id: str,
        project_id: str,
        series_id: str | None = None,
        profile: ExportProfile = VERTICAL_1080_1920,
        subtitle_language: str = "en",
    ) -> tuple[Asset, EpisodeRender, QCResult]:
        render_asset, render = await self._assembly_service.render_episode(
            episode_id, project_id, series_id=series_id,
            output=profile.output, subtitle_language=subtitle_language,
        )
        data = await self._asset_service.read_bytes(render_asset.id)
        probe = await self._inspector.inspect(data)
        subtitle_cues = await self._subtitle_repo.list_by_episode(episode_id, subtitle_language)
        report = validate_export(
            probe,
            profile.output,
            expected_duration_seconds=render_asset.duration_seconds,
            subtitle_cues=subtitle_cues,
        )
        return render_asset, render, report
