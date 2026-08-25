"""MODULE-076 - failure-simulation matrix: timeout, rate limit, quota,
corrupt media, worker crash/restart, unavailable provider, failed QC -
plus "no duplicate accepted assets" and "unrecoverable jobs become
inspectable rather than hanging."

Every scenario here already has *some* coverage scattered across other
modules' test files (this module is largely an audit, not new
capability); this file exists to make the failure matrix itself
inspectable in one place, and adds the handful of angles nothing else
covered (a worker crashing mid-batch with a second untouched job still
queued; retrying past a corrupt/rate-limited attempt never leaving two
accepted assets for the same shot).
"""

import json

import pytest

import fixtures as fx
from xerama.config import ModelRoleRegistry, Settings
from xerama.domain.enums import (
    JobStage,
    JobStatus,
    MediaQCDimension,
    ModelRole,
    ProviderErrorKind,
    QCStatus,
)
from xerama.domain.quality import QCResult
from xerama.domain.story import ConceptCandidate
from xerama.pipeline.ai_gateway import AIGateway, XeramaGenerationError
from xerama.pipeline.media_qc_checks import check_media_health
from xerama.providers.errors import ProviderError
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyMediaQCRepository,
    SQLAlchemyProjectRepository,
)
from xerama.services.asset_service import AssetService
from xerama.services.media_qc_service import MediaQCService, QCGateBlockedError
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError
from xerama.services.retake_service import MAX_AUTO_RETAKE_ATTEMPTS
from xerama.worker.job_worker import JobWorker


def _gateway(responses: list) -> AIGateway:
    return AIGateway(
        provider=FakeLLMProvider(responses),
        roles=ModelRoleRegistry(Settings()),
        health=ProviderHealthTracker(),
        max_attempts=3,
    )


# --- 1. timeout ------------------------------------------------------------


async def test_timeout_is_retried_and_recovers_within_budget() -> None:
    gateway = _gateway(
        [
            ProviderError(ProviderErrorKind.TIMEOUT, "gateway timed out"),
            json.dumps(fx.concept("A")),
        ]
    )
    result = await gateway.generate(
        role=ModelRole.CONCEPT_GENERATOR_A, schema=ConceptCandidate,
        system_prompt="s", user_prompt="u",
    )
    assert result.title == "A"


async def test_timeout_exhausting_the_retry_budget_fails_cleanly_not_a_hang() -> None:
    gateway = _gateway([ProviderError(ProviderErrorKind.TIMEOUT, "t")] * 3)
    with pytest.raises(XeramaGenerationError):
        await gateway.generate(
            role=ModelRole.CONCEPT_GENERATOR_A, schema=ConceptCandidate,
            system_prompt="s", user_prompt="u",
        )


# --- 2. rate limit (provider-side) -----------------------------------------


async def test_rate_limited_provider_falls_back_to_a_healthy_one() -> None:
    from xerama.providers.image import ImageGenerationRequest

    limited = FakeImageProvider([ProviderError(ProviderErrorKind.RATE_LIMIT, "429")], name="limited")
    healthy = FakeImageProvider([b"ok"], name="healthy")
    router = MediaProviderRouter([limited, healthy])
    request = ImageGenerationRequest(prompt="a shot")

    selected, data, attempts = await router.generate(
        lambda p: True, lambda p: p.generate(request, [])
    )
    assert selected is healthy
    assert data == b"ok"
    assert [a.outcome for a in attempts] == ["failed", "selected"]


# --- 3. quota (non-retriable - must not burn the retry budget) -------------


async def test_quota_exhaustion_fails_on_the_first_attempt_not_retried() -> None:
    provider = FakeLLMProvider([ProviderError(ProviderErrorKind.QUOTA, "quota exhausted")])
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()), health=ProviderHealthTracker())

    with pytest.raises(XeramaGenerationError):
        await gateway.generate(
            role=ModelRole.CONCEPT_GENERATOR_A, schema=ConceptCandidate,
            system_prompt="s", user_prompt="u",
        )
    # Exactly one call - QUOTA is not in RETRIABLE_KINDS, so no wasted
    # retry budget is burned on a definitively-exhausted quota.
    assert len(provider.calls) == 1


# --- 4. corrupt media --------------------------------------------------------


async def test_corrupt_media_zero_bytes_blocks_media_health_check() -> None:
    from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType

    corrupt_asset = Asset(
        id="A1", type=AssetType.IMAGE, storage_path="x", content_hash="h", size_bytes=0,
        ownership=AssetOwnership(project_id="P1"), provenance=AssetProvenance(provider="p"),
    )
    result = check_media_health(corrupt_asset)
    assert result.status == QCStatus.BLOCK
    assert any("size_bytes" in r for r in result.reasons)


async def test_corrupt_media_blocks_the_accept_gate(session, tmp_path) -> None:
    from xerama.providers.local_storage import LocalStorageProvider

    storage = LocalStorageProvider(tmp_path / "storage")
    asset_service = AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))
    media_qc = MediaQCService(
        repo=SQLAlchemyMediaQCRepository(session), asset_service=asset_service,
        provider=FakeMediaQCProvider(),
    )
    from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetType

    asset = await asset_service.ingest_bytes(
        b"", AssetType.IMAGE, AssetOwnership(project_id="P1"),
        provenance=AssetProvenance(provider="p"), mime_type="image/png",
    )
    with pytest.raises(QCGateBlockedError):
        await media_qc.run_gate(asset.id, [MediaQCDimension.MEDIA_HEALTH])
    persisted = await asset_service.get(asset.id)
    assert persisted.status.value == "pending"  # never silently accepted


# --- 5/6. worker crash + restart --------------------------------------------


async def test_worker_crash_leaves_a_second_untouched_job_available(session) -> None:
    """A worker crashing while holding one job's lease must not affect a
    second, never-claimed job - only the abandoned one is recoverable,
    the untouched one is claimable normally the whole time."""
    project = await SQLAlchemyProjectRepository(session).create("p")
    job_repo = SQLAlchemyJobRepository(session)
    job_a = await job_repo.enqueue(project.id, JobStage.CONCEPT_GENERATION, payload={"i": "a"})
    job_b = await job_repo.enqueue(project.id, JobStage.JUDGE, payload={"i": "b"})
    await session.commit()

    # "Worker 1" claims job A then crashes (lease immediately expired).
    claimed_a = await job_repo.claim("worker-1", lease_seconds=-1)
    await session.commit()
    assert claimed_a.id == job_a.id

    # Job B was never touched - a normal claim (unrelated to recovery)
    # still works for it right now.
    claimed_b = await job_repo.claim("worker-2", lease_seconds=60)
    await session.commit()
    assert claimed_b.id == job_b.id

    # Recovery only ever touches the abandoned job.
    worker = JobWorker(job_repo=job_repo, worker_id="worker-3")
    recovered = await worker.reclaim_abandoned()
    await session.commit()
    assert [j.id for j in recovered] == [job_a.id]

    still_running_b = await job_repo.get(job_b.id)
    assert still_running_b.status == JobStatus.RUNNING  # untouched by the unrelated recovery


# --- 7. unavailable provider -------------------------------------------------


async def test_no_eligible_provider_fails_immediately_not_a_hang() -> None:
    router = MediaProviderRouter([])
    with pytest.raises(NoEligibleProviderError) as exc_info:
        await router.generate(lambda p: True, lambda p: p.generate(None, []))
    # The failure is inspectable, not opaque - every attempt (here, none)
    # is enumerated in the exception.
    assert exc_info.value.attempts == []


# --- 8. failed QC (exhausted auto-retake budget -> escalation, not a hang) -


async def test_failed_qc_past_the_retry_budget_escalates_and_never_accepts(session, tmp_path) -> None:
    from xerama.providers.local_storage import LocalStorageProvider
    from xerama.services.retake_service import AutomaticRetakeService
    from xerama.services.storyboard_service import StoryboardService
    from xerama.repositories.sqlalchemy_impl import SQLAlchemyStoryboardRepository

    # A QC provider that always BLOCKs, however many times it's asked -
    # simulates a genuinely broken/uncorrectable generation.
    always_blocked = FakeMediaQCProvider(
        [
            QCResult(gate=MediaQCDimension.IDENTITY.value, status=QCStatus.BLOCK, score=1.0, reasons=["bad"])
            for _ in range(MAX_AUTO_RETAKE_ATTEMPTS + 2)
        ]
    )
    storage = LocalStorageProvider(tmp_path / "storage")
    asset_service = AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))
    media_qc = MediaQCService(
        repo=SQLAlchemyMediaQCRepository(session), asset_service=asset_service, provider=always_blocked
    )
    storyboard_repo = SQLAlchemyStoryboardRepository(session)
    storyboard_service = StoryboardService(
        storyboard_repo=storyboard_repo, asset_service=asset_service, media_qc=media_qc
    )

    storyboard = await storyboard_service.get_or_create_storyboard("EP1", 1, 1)
    await session.commit()

    image_provider = FakeImageProvider([b"take"] * (MAX_AUTO_RETAKE_ATTEMPTS + 2))
    image_router = MediaProviderRouter([image_provider])
    retake_service = AutomaticRetakeService()

    from xerama.domain.generation_request import CompiledReferences, ShotGenerationRequest
    from xerama.domain.scene import Camera, ProviderRequirements, Visual
    from xerama.domain.enums import AudioMode

    request = ShotGenerationRequest(
        shot_number=1, scene_number=1, prompt="p", duration_seconds=5.0, camera=Camera(),
        visual=Visual(), audio_mode=AudioMode.NATIVE, references=CompiledReferences(),
        provider_requirements=ProviderRequirements(),
    )

    with pytest.raises(QCGateBlockedError):
        await storyboard_service.generate_with_auto_heal(
            storyboard.id, "P1", request, image_router, retake_service
        )
    await session.commit()

    escalated = await storyboard_service.get(storyboard.id)
    assert escalated.escalated is True  # inspectable, not hanging
    assert escalated.auto_retake_attempts >= MAX_AUTO_RETAKE_ATTEMPTS

    # No duplicate accepted assets: every take this loop generated was
    # rejected, none accepted, despite repeated retries.
    assets = await SQLAlchemyAssetRepository(session).list_by_ownership("P1")
    keyframe_assets = [a for a in assets if a.type.value == "image"]
    assert keyframe_assets  # attempts really were made
    assert all(a.status.value == "rejected" for a in keyframe_assets)


# --- unrecoverable jobs become inspectable, not stuck -----------------------


async def test_non_retriable_job_failure_dead_letters_immediately_and_is_listable(session) -> None:
    project = await SQLAlchemyProjectRepository(session).create("p")
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project.id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()
    claimed = await job_repo.claim("worker-1")
    await session.commit()

    failed = await job_repo.fail_job_attempt(claimed.id, "unrecoverable: bad config", retriable=False)
    await session.commit()

    assert failed.status == JobStatus.FAILED  # terminal, not stuck in RUNNING
    listed = await job_repo.list_failed(project.id)
    assert [j.id for j in listed] == [job.id]  # inspectable via the normal query path
