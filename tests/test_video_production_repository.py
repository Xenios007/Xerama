from xerama.repositories.sqlalchemy_impl import SQLAlchemyVideoProductionRepository

from test_storyboard_repository import _episode


async def test_get_or_create_is_idempotent_per_shot(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyVideoProductionRepository(session)

    first = await repo.get_or_create(episode_id, 1, 1, continuity_group="GRP_A")
    await session.commit()
    second = await repo.get_or_create(episode_id, 1, 1)
    assert first.id == second.id
    assert second.continuity_group == "GRP_A"

    other_shot = await repo.get_or_create(episode_id, 1, 2, continuity_group="GRP_A")
    assert other_shot.id != first.id


async def test_get_returns_none_for_unknown(session) -> None:
    repo = SQLAlchemyVideoProductionRepository(session)
    assert await repo.get("does-not-exist") is None


async def test_get_previous_in_continuity_group_finds_immediate_predecessor(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyVideoProductionRepository(session)
    await repo.get_or_create(episode_id, 1, 1, continuity_group="GRP_A")
    await repo.get_or_create(episode_id, 1, 2, continuity_group="GRP_A")
    await session.commit()

    predecessor = await repo.get_previous_in_continuity_group(episode_id, "GRP_A", 1, 2)
    assert predecessor is not None
    assert (predecessor.scene_number, predecessor.shot_number) == (1, 1)

    none_before_first = await repo.get_previous_in_continuity_group(episode_id, "GRP_A", 1, 1)
    assert none_before_first is None


async def test_get_previous_in_continuity_group_ignores_other_groups(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyVideoProductionRepository(session)
    await repo.get_or_create(episode_id, 1, 1, continuity_group="GRP_A")
    await repo.get_or_create(episode_id, 1, 2, continuity_group="GRP_B")
    await session.commit()

    predecessor = await repo.get_previous_in_continuity_group(episode_id, "GRP_B", 1, 2)
    assert predecessor is None  # shot 1 belongs to a different continuity group


async def test_approve_sets_status_and_approved_asset(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyVideoProductionRepository(session)
    production = await repo.get_or_create(episode_id, 1, 1)
    await session.commit()

    approved = await repo.approve(production.id, "asset-123")
    await session.commit()
    assert approved.status == "approved"
    assert approved.approved_take_asset_id == "asset-123"


async def test_set_extracted_last_frame(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyVideoProductionRepository(session)
    production = await repo.get_or_create(episode_id, 1, 1, continuity_group="GRP_A")
    await session.commit()

    updated = await repo.set_extracted_last_frame(production.id, "frame-asset-1")
    await session.commit()
    assert updated.extracted_last_frame_asset_id == "frame-asset-1"


async def test_list_by_episode(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyVideoProductionRepository(session)
    await repo.get_or_create(episode_id, 1, 1)
    await repo.get_or_create(episode_id, 1, 2)
    await session.commit()

    productions = await repo.list_by_episode(episode_id)
    assert len(productions) == 2
