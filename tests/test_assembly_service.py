import pytest

from xerama.domain.asset import AssetOwnership, AssetType
from xerama.domain.brief import CreativeBrief
from xerama.domain.enums import AudioMode, CliffhangerType
from xerama.domain.episode import Cliffhanger, EpisodeOutline
from xerama.domain.scene import Camera, EpisodeShotPlan, Scene, Shot, Visual
from xerama.domain.story import ConceptCandidate, Protagonist
from xerama.domain.subtitle import SubtitleCue
from xerama.pipeline.assembly_plan_builder import IncompleteProductionError
from xerama.providers.fake_assembler import FakeAssembler
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyAudioProductionRepository,
    SQLAlchemyEpisodeRenderRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyMusicCueRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeriesRepository,
    SQLAlchemySoundEffectCueRepository,
    SQLAlchemySubtitleCueRepository,
    SQLAlchemyVideoProductionRepository,
)
from xerama.services.assembly_service import EpisodeAssemblyService
from xerama.services.asset_service import AssetService


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


def _brief() -> CreativeBrief:
    return CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)


def _candidate() -> ConceptCandidate:
    return ConceptCandidate(
        title="T",
        genre=["thriller"],
        logline="A woman uncovers her sister's secret double life.",
        premise="premise",
        protagonist=Protagonist(name="Mara", role="protagonist", desire="the truth", flaw="pride"),
        antagonistic_force="her own family",
        central_conflict="loyalty vs. justice",
        central_secret="the sister faked her death",
        emotional_engine="betrayal",
        opening_hook="a funeral, and a text message from the dead",
        serial_engine="who else is lying",
        ending_direction="reconciliation or ruin",
    )


async def _episode_setup(session) -> tuple[str, str, str]:
    project = await SQLAlchemyProjectRepository(session).create("p")
    series = await SQLAlchemySeriesRepository(session).create_series(project.id, _brief(), _candidate())
    episode = await SQLAlchemyEpisodeRepository(session).save_outline(
        series.id,
        EpisodeOutline(
            episode_number=1,
            objective="find the truth",
            opening_hook="a scream",
            stakes="freedom",
            conflict="sister vs sister",
            turn="the letter was fake",
            reveal="he was never who he claimed",
            duration_target_seconds=75,
            cliffhanger=Cliffhanger(type=CliffhangerType.IDENTITY_REVEAL, event="the mask comes off"),
        ),
    )
    await session.commit()
    return project.id, series.id, episode.id


def _shot_plan(*, audio_mode: AudioMode = AudioMode.NATIVE) -> EpisodeShotPlan:
    return EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apartment",
                characters=["CHAR_001"],
                shots=[
                    Shot(
                        shot_number=1,
                        scene_number=1,
                        character_ids=["CHAR_001"],
                        action="Mara opens the letter",
                        duration_seconds=5.0,
                        camera=Camera(shot_size="close-up"),
                        visual=Visual(),
                        audio_mode=audio_mode,
                    )
                ],
            )
        ],
    )


def _service(session, storage, assembler=None) -> EpisodeAssemblyService:
    return EpisodeAssemblyService(
        episode_repo=SQLAlchemyEpisodeRepository(session),
        video_production_repo=SQLAlchemyVideoProductionRepository(session),
        audio_production_repo=SQLAlchemyAudioProductionRepository(session),
        music_cue_repo=SQLAlchemyMusicCueRepository(session),
        sfx_cue_repo=SQLAlchemySoundEffectCueRepository(session),
        subtitle_repo=SQLAlchemySubtitleCueRepository(session),
        render_repo=SQLAlchemyEpisodeRenderRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        assembler=assembler or FakeAssembler(),
    )


async def _approve_video_take(session, storage, episode_id: str, data: bytes = b"clip") -> str:
    asset_service = AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))
    asset = await asset_service.ingest_bytes(
        data, AssetType.VIDEO,
        AssetOwnership(project_id="ignored", episode_id=episode_id, scene_number=1, shot_number=1),
        duration_seconds=5.0,
    )
    video_repo = SQLAlchemyVideoProductionRepository(session)
    production = await video_repo.get_or_create(episode_id, 1, 1)
    await video_repo.approve(production.id, asset.id)
    await session.commit()
    return asset.id


async def test_render_episode_ingests_asset_and_creates_v1_render(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    service = _service(session, storage)
    render_asset, render = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()

    assert render_asset.type.value == "video"
    assert render_asset.take_number == 1
    assert render_asset.duration_seconds == 5.0
    assert "render_manifest" in render_asset.provenance.generation_params

    assert render.version == 1
    assert render.status == "draft"
    assert render.source_script_version == 1
    assert render.render_asset_id == render_asset.id
    assert render.parent_render_id is None


async def test_render_episode_raises_on_incomplete_production(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()

    service = _service(session, storage)
    with pytest.raises(IncompleteProductionError):
        await service.render_episode(episode_id, project_id, series_id=series_id)


async def test_second_render_is_version_2_with_parent_link(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    service = _service(session, storage)
    _, first = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()
    await service.approve_render(first.id)
    await session.commit()

    _, second = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()

    assert second.version == 2
    assert second.parent_render_id == first.id


async def test_approve_render_supersedes_previous_current(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    service = _service(session, storage)
    _, first = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()
    await service.approve_render(first.id)
    await session.commit()
    _, second = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()
    await service.approve_render(second.id)
    await session.commit()

    current = await service.get_current(episode_id)
    assert current.id == second.id

    superseded_first = await service.get_render(first.id)
    assert superseded_first.status == "superseded"


async def test_rollback_reapproves_an_older_render(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    service = _service(session, storage)
    _, first = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()
    await service.approve_render(first.id)
    await session.commit()
    _, second = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()
    await service.approve_render(second.id)
    await session.commit()

    # Roll back to the first version.
    await service.approve_render(first.id)
    await session.commit()

    current = await service.get_current(episode_id)
    assert current.id == first.id
    superseded_second = await service.get_render(second.id)
    assert superseded_second.status == "superseded"


async def test_staleness_detects_changed_input_asset(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id, data=b"clip-v1")

    service = _service(session, storage)
    _, render = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()

    stale, reasons = await service.check_staleness(render.id)
    assert stale is False
    assert reasons == []

    # A shot's video take gets regenerated and re-approved with new content.
    await _approve_video_take(session, storage, episode_id, data=b"clip-v2")

    stale, reasons = await service.check_staleness(render.id)
    assert stale is True
    assert reasons


async def test_render_includes_exported_subtitles_when_present(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    subtitle_repo = SQLAlchemySubtitleCueRepository(session)
    await subtitle_repo.replace_track(
        episode_id,
        "en",
        [
            {
                "scene_number": 1,
                "shot_number": 1,
                "character_id": "CHAR_001",
                "text": "This can't be real.",
                "lines": ["This can't be real."],
                "start_seconds": 0.0,
                "end_seconds": 5.0,
            }
        ],
    )
    await session.commit()

    assembler = FakeAssembler()
    service = _service(session, storage, assembler)
    render_asset, _ = await service.render_episode(episode_id, project_id, series_id=series_id)
    await session.commit()

    assert assembler.calls[0].subtitle_asset_id is not None
    assert render_asset.provenance.generation_params["render_manifest"]["plan"]["subtitle_asset_id"]
