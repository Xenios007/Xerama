"""MODULE-074 - integration tests across subsystem boundaries (API/
persistence, queue/worker, storage, providers), run with `pytest -m
integration` (see docs/TESTING.md). Every read-back in this file uses a
*fresh* session/connection, not the one that wrote the data - proving
persistence actually round-tripped through the DB, not just an
in-memory Python object still held by the writing test.
"""

import json
import shutil

import pytest
import pytest_asyncio

import fixtures as fx
from xerama.config import ModelRoleRegistry, Settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetStatus, AssetType
from xerama.domain.brief import CreativeBrief
from xerama.domain.enums import JobStage, JobStatus, MediaQCDimension
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.orchestrator import Showrunner
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyConceptRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyMediaQCRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeasonRepository,
    SQLAlchemySeriesRepository,
)
from xerama.services.asset_service import AssetService
from xerama.services.media_qc_service import MediaQCService
from xerama.worker.job_worker import JobWorker

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    db_path = tmp_path / "integration.db"
    engine = make_engine(f"sqlite+aiosqlite:///{db_path}")
    await create_all(engine)
    factory = make_session_factory(engine)
    yield factory
    await engine.dispose()


# --- story pipeline through persistence -------------------------------


async def test_story_pipeline_persists_across_a_fresh_session(session_factory) -> None:
    async with session_factory() as session:
        project = await SQLAlchemyProjectRepository(session).create("Integration Test")
        provider = FakeLLMProvider(
            [
                json.dumps(fx.concept("A")),
                json.dumps(fx.concept("B")),
                json.dumps(fx.judge_result("A")),
                json.dumps(fx.bible()),
                json.dumps(fx.cast()),
                json.dumps(fx.season_plan()),
                json.dumps(fx.outline_set(3)),
                json.dumps(fx.script()),
                json.dumps(fx.shot_plan()),
            ]
        )
        gateway = AIGateway(
            provider=provider, roles=ModelRoleRegistry(Settings()), health=ProviderHealthTracker()
        )
        showrunner = Showrunner(
            gateway=gateway,
            concept_repo=SQLAlchemyConceptRepository(session),
            series_repo=SQLAlchemySeriesRepository(session),
            season_repo=SQLAlchemySeasonRepository(session),
            episode_repo=SQLAlchemyEpisodeRepository(session),
            job_repo=SQLAlchemyJobRepository(session),
        )
        brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)
        result = await showrunner.run(project.id, brief)
        await session.commit()
        series_id = result.series_id

    # A brand-new session/connection - not the one that wrote this data.
    async with session_factory() as fresh_session:
        series = await SQLAlchemySeriesRepository(fresh_session).get_series(series_id)
        assert series is not None
        assert series.project_id == project.id

        episodes = await SQLAlchemyEpisodeRepository(fresh_session).list_by_series(series_id)
        assert len(episodes) == 3

        bible = await SQLAlchemySeriesRepository(fresh_session).get_bible(series_id)
        assert bible is not None
        assert bible.title == "Blood Sisters"


# --- queued fake media generation through the asset/QC lifecycle -------


async def test_media_generation_through_asset_qc_lifecycle_persists(session_factory, tmp_path) -> None:
    async with session_factory() as session:
        storage = LocalStorageProvider(tmp_path / "storage")
        asset_service = AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))
        media_qc = MediaQCService(
            repo=SQLAlchemyMediaQCRepository(session),
            asset_service=asset_service,
            provider=FakeMediaQCProvider(),  # defaults to PASS
        )

        asset = await asset_service.ingest_bytes(
            b"fake keyframe bytes",
            AssetType.IMAGE,
            AssetOwnership(project_id="P1"),
            provenance=AssetProvenance(provider="fake_image"),
            mime_type="image/png",
        )
        await media_qc.run_check(asset.id, MediaQCDimension.IDENTITY)
        accepted = await asset_service.accept(asset.id)
        await session.commit()
        assert accepted.status == AssetStatus.ACCEPTED
        asset_id = asset.id

    async with session_factory() as fresh_session:
        asset_repo = SQLAlchemyAssetRepository(fresh_session)
        persisted_asset = await asset_repo.get(asset_id)
        assert persisted_asset is not None
        assert persisted_asset.status == AssetStatus.ACCEPTED

        qc_attempts = await SQLAlchemyMediaQCRepository(fresh_session).list_by_asset(asset_id)
        assert len(qc_attempts) == 1
        assert qc_attempts[0].dimension == MediaQCDimension.IDENTITY


# --- API-worker restart/resume ------------------------------------------


async def test_worker_restart_resumes_and_completes_an_abandoned_job(session_factory) -> None:
    """Simulates a real crash/restart: "worker A" claims a job and never
    heartbeats/succeeds/fails it (its lease expires); a completely
    separate "worker B" instance (its own session, matching how a
    restarted process would reconnect) reclaims the abandoned lease and
    processes the job to completion."""
    async with session_factory() as session:
        project = await SQLAlchemyProjectRepository(session).create("p")
        job = await SQLAlchemyJobRepository(session).enqueue(
            project.id, JobStage.CONCEPT_GENERATION, payload={}
        )
        await session.commit()
        job_id = job.id

    async with session_factory() as session_a:
        # A negative lease is already-expired the instant it's granted -
        # simulates real wall-clock time passing after worker A crashed.
        claimed = await SQLAlchemyJobRepository(session_a).claim("worker-a", lease_seconds=-1)
        await session_a.commit()
        assert claimed is not None and claimed.id == job_id

    async with session_factory() as session_b:
        job_repo_b = SQLAlchemyJobRepository(session_b)
        worker_b = JobWorker(job_repo=job_repo_b, worker_id="worker-b")

        recovered = await worker_b.reclaim_abandoned()
        await session_b.commit()
        assert [r.id for r in recovered] == [job_id]

        processed_ids = []

        async def handler(claimed_job):
            processed_ids.append(claimed_job.id)
            return ["asset-from-worker-b"]

        worker_b.register_handler(JobStage.CONCEPT_GENERATION, handler)
        did_process = await worker_b.run_once()
        await session_b.commit()
        assert did_process is True
        assert processed_ids == [job_id]

    async with session_factory() as verify_session:
        final = await SQLAlchemyJobRepository(verify_session).get(job_id)
        assert final is not None
        assert final.status == JobStatus.SUCCEEDED
        assert final.result_asset_ids == ["asset-from-worker-b"]


# --- real FFmpeg integration, conditional on the binary being installed -


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed - see docs/DEPLOYMENT.md")
async def test_real_ffmpeg_extracts_the_last_frame_of_a_synthetic_clip(tmp_path) -> None:
    """Generates a tiny synthetic clip with ffmpeg's own `lavfi` test-
    source (no external sample-video fixture needed), then runs the
    *real* `FFmpegFrameExtractor` against it - the one path this
    codebase's test suite otherwise never exercises for real (see
    docs/TESTING.md section 3)."""
    import asyncio

    from xerama.providers.ffmpeg_frame_extractor import FFmpegFrameExtractor

    clip_path = tmp_path / "synthetic.mp4"
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=64x64:d=1", "-frames:v", "10",
        str(clip_path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await process.communicate()
    assert clip_path.exists(), "failed to synthesize a test clip with ffmpeg - environment issue, not the extractor"

    extractor = FFmpegFrameExtractor()
    frame_bytes = await extractor.extract_last_frame(clip_path.read_bytes())
    assert len(frame_bytes) > 0
    assert frame_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # a real PNG signature, not a placeholder


@pytest.mark.skipif(
    shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None,
    reason="ffmpeg/ffprobe not installed - see docs/DEPLOYMENT.md",
)
async def test_real_ffprobe_inspects_a_synthetic_clip(tmp_path) -> None:
    import asyncio

    from xerama.providers.ffprobe_inspector import FFprobeInspector

    clip_path = tmp_path / "synthetic.mp4"
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1", "-t", "1", str(clip_path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await process.communicate()
    assert clip_path.exists()

    inspector = FFprobeInspector()
    result = await inspector.inspect(clip_path.read_bytes())
    assert result.ok is True
    assert result.has_video_stream is True
    assert result.width == 64
    assert result.height == 64
