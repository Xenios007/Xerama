"""Episode assembly + versioning service (MODULE-046/047).

Builds a deterministic `AssemblyPlan` from every approved production
asset for an episode, resolves referenced asset bytes, hands them to an
`EpisodeAssembler`, and persists the result as a new take-numbered episode
`Asset` plus a new `EpisodeRender` version - a render is never silently
overwritten, and its manifest/consumed-asset-ids stay attached for audit
and staleness checking.
"""

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType
from xerama.domain.assembly import OutputSpec, RenderManifest
from xerama.domain.episode_render import EpisodeRender
from xerama.pipeline.assembly_plan_builder import IncompleteProductionError, build_assembly_plan
from xerama.pipeline.render_staleness import check_staleness
from xerama.pipeline.subtitle_generation import export_srt
from xerama.providers.assembler import EpisodeAssembler
from xerama.repositories.interfaces import (
    AudioProductionRepository,
    EpisodeRenderRepository,
    EpisodeRepository,
    MusicCueRepository,
    SoundEffectCueRepository,
    SubtitleCueRepository,
    VideoProductionRepository,
)
from xerama.services.asset_service import AssetService


class EpisodeAssemblyService:
    def __init__(
        self,
        episode_repo: EpisodeRepository,
        video_production_repo: VideoProductionRepository,
        audio_production_repo: AudioProductionRepository,
        music_cue_repo: MusicCueRepository,
        sfx_cue_repo: SoundEffectCueRepository,
        subtitle_repo: SubtitleCueRepository,
        render_repo: EpisodeRenderRepository,
        asset_service: AssetService,
        assembler: EpisodeAssembler,
    ) -> None:
        self._episode_repo = episode_repo
        self._video_production_repo = video_production_repo
        self._audio_production_repo = audio_production_repo
        self._music_cue_repo = music_cue_repo
        self._sfx_cue_repo = sfx_cue_repo
        self._subtitle_repo = subtitle_repo
        self._render_repo = render_repo
        self._asset_service = asset_service
        self._assembler = assembler

    async def _current_plan_inputs(self, episode_id: str) -> set[str]:
        """The asset ids `build_assembly_plan` would use *right now* - the
        reference point staleness checks compare a past render against."""
        plan_data = await self._episode_repo.get_shot_plan(episode_id)
        if plan_data is None:
            return set()
        video_productions = await self._video_production_repo.list_by_episode(episode_id)
        audio_productions = await self._audio_production_repo.list_by_episode(episode_id)
        music_cues = await self._music_cue_repo.list_by_episode(episode_id)
        sfx_cues = await self._sfx_cue_repo.list_by_episode(episode_id)
        try:
            plan = build_assembly_plan(
                episode_id, plan_data, video_productions, audio_productions, music_cues, sfx_cues
            )
        except IncompleteProductionError:
            return set()
        return {c.asset_id for c in plan.clips} | {a.asset_id for a in plan.audio_tracks}

    async def render_episode(
        self,
        episode_id: str,
        project_id: str,
        series_id: str | None = None,
        output: OutputSpec | None = None,
        subtitle_language: str = "en",
    ) -> tuple[Asset, EpisodeRender]:
        episode = await self._episode_repo.get(episode_id)
        if episode is None:
            raise ValueError(f"episode {episode_id} not found")
        plan_data = await self._episode_repo.get_shot_plan(episode_id)
        if plan_data is None:
            raise ValueError(f"episode {episode_id} has no shot plan yet")

        video_productions = await self._video_production_repo.list_by_episode(episode_id)
        audio_productions = await self._audio_production_repo.list_by_episode(episode_id)
        music_cues = await self._music_cue_repo.list_by_episode(episode_id)
        sfx_cues = await self._sfx_cue_repo.list_by_episode(episode_id)
        subtitle_cues = await self._subtitle_repo.list_by_episode(episode_id, subtitle_language)

        subtitle_asset_id = None
        if subtitle_cues:
            srt_text = export_srt(subtitle_cues)
            subtitle_asset = await self._asset_service.ingest_bytes(
                srt_text.encode("utf-8"),
                AssetType.SUBTITLE,
                AssetOwnership(project_id=project_id, series_id=series_id, episode_id=episode_id),
                provenance=AssetProvenance(provider="subtitle_export"),
                mime_type="text/srt",
                ext=".srt",
            )
            subtitle_asset_id = subtitle_asset.id

        plan = build_assembly_plan(
            episode_id,
            plan_data,
            video_productions,
            audio_productions,
            music_cues,
            sfx_cues,
            subtitle_asset_id=subtitle_asset_id,
            output=output,
        )

        input_asset_ids = sorted(
            {clip.asset_id for clip in plan.clips}
            | {track.asset_id for track in plan.audio_tracks}
            | ({subtitle_asset_id} if subtitle_asset_id else set())
        )
        inputs: dict[str, bytes] = {}
        content_hashes: dict[str, str] = {}
        for asset_id in input_asset_ids:
            asset = await self._asset_service.get(asset_id)
            if asset is None:
                raise ValueError(f"assembly input asset {asset_id} not found")
            inputs[asset_id] = await self._asset_service.read_bytes(asset_id)
            content_hashes[asset_id] = asset.content_hash

        data, commands = await self._assembler.assemble(plan, inputs)

        manifest = RenderManifest(
            plan=plan,
            input_content_hashes=content_hashes,
            ffmpeg_commands=commands,
            output_duration_seconds=plan.total_duration_seconds,
        )

        existing_renders = await self._render_repo.list_by_episode(episode_id)
        take_number = max((r.version for r in existing_renders), default=0) + 1

        render_asset = await self._asset_service.ingest_bytes(
            data,
            AssetType.VIDEO,
            AssetOwnership(project_id=project_id, series_id=series_id, episode_id=episode_id),
            provenance=AssetProvenance(
                provider="ffmpeg_assembler",
                source_reference_asset_ids=input_asset_ids,
                generation_params={"render_manifest": manifest.model_dump(mode="json")},
            ),
            mime_type="video/mp4",
            ext=".mp4",
            duration_seconds=plan.total_duration_seconds,
            width=plan.output.width,
            height=plan.output.height,
            take_number=take_number,
        )

        current = await self._render_repo.get_current(episode_id)
        render = await self._render_repo.create(
            episode_id=episode_id,
            render_asset_id=render_asset.id,
            source_script_version=episode.version,
            input_asset_ids=input_asset_ids,
            parent_render_id=current.id if current else None,
        )
        return render_asset, render

    async def get_render(self, render_id: str) -> EpisodeRender:
        render = await self._render_repo.get(render_id)
        if render is None:
            raise ValueError(f"episode render {render_id} not found")
        return render

    async def approve_render(self, render_id: str) -> EpisodeRender:
        """Also how rollback works - approving an older `superseded`
        render makes it current again without touching its content."""
        return await self._render_repo.approve(render_id)

    async def get_current(self, episode_id: str) -> EpisodeRender | None:
        return await self._render_repo.get_current(episode_id)

    async def list_renders(self, episode_id: str) -> list[EpisodeRender]:
        return await self._render_repo.list_by_episode(episode_id)

    async def check_staleness(self, render_id: str) -> tuple[bool, list[str]]:
        render = await self.get_render(render_id)
        episode = await self._episode_repo.get(render.episode_id)
        if episode is None:
            raise ValueError(f"episode {render.episode_id} not found")
        current_input_asset_ids = await self._current_plan_inputs(render.episode_id)
        return check_staleness(render, episode.version, current_input_asset_ids)
