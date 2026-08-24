from xerama.domain.enums import QCStatus
from xerama.domain.scene import Camera, EpisodeShotPlan, Scene, Shot, Visual
from xerama.repositories.sqlalchemy_impl import SQLAlchemySubtitleCueRepository
from xerama.services.subtitle_service import SubtitleService

from test_storyboard_repository import _episode


def _plan() -> EpisodeShotPlan:
    return EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apt",
                shots=[
                    Shot(
                        shot_number=1,
                        scene_number=1,
                        duration_seconds=5.0,
                        camera=Camera(),
                        visual=Visual(),
                        dialogue="This can't be real.",
                        character_ids=["CHAR_001"],
                    )
                ],
            )
        ],
    )


def _service(session) -> SubtitleService:
    return SubtitleService(repo=SQLAlchemySubtitleCueRepository(session))


async def test_generate_track_persists_cues(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)

    cues = await service.generate_track(episode_id, _plan())
    await session.commit()
    assert len(cues) == 1
    assert cues[0].text == "This can't be real."


async def test_export_srt_contains_expected_timing_and_text(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    await service.generate_track(episode_id, _plan())
    await session.commit()

    srt = await service.export_srt(episode_id)
    assert "00:00:00,000 --> 00:00:05,000" in srt
    assert "This can't be real." in srt


async def test_validate_readability_passes_for_generated_track(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    await service.generate_track(episode_id, _plan())
    await session.commit()

    result = await service.validate_readability(episode_id)
    assert result.status == QCStatus.PASS


async def test_regenerating_track_replaces_not_accumulates(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    await service.generate_track(episode_id, _plan())
    await session.commit()
    await service.generate_track(episode_id, _plan())
    await session.commit()

    cues = await service.list_by_episode(episode_id)
    assert len(cues) == 1
