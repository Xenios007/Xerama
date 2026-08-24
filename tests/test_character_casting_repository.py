import pytest

from xerama.domain.asset import AssetOwnership, AssetType
from xerama.domain.brief import CreativeBrief
from xerama.domain.character import Character, CharacterCast
from xerama.domain.story import Protagonist, ConceptCandidate
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyCharacterCastingRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeriesRepository,
)


def _candidate() -> ConceptCandidate:
    return ConceptCandidate(
        title="T",
        genre=["thriller"],
        logline="logline",
        premise="premise",
        protagonist=Protagonist(name="Mara", role="protagonist", desire="truth", flaw="pride"),
        antagonistic_force="family",
        central_conflict="loyalty vs justice",
        central_secret="a secret",
        emotional_engine="betrayal",
        opening_hook="hook",
        serial_engine="engine",
        ending_direction="direction",
    )


async def _character(session) -> tuple[str, str]:
    """Creates a project -> series -> one-character cast. Returns (project_id, character_id)."""
    project = await SQLAlchemyProjectRepository(session).create("p")
    series_repo = SQLAlchemySeriesRepository(session)
    series = await series_repo.create_series(
        project.id, CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75), _candidate()
    )
    await series_repo.save_cast(
        series.id,
        CharacterCast(characters=[Character(id="CHAR_001", name="Mara", role="protagonist")]),
    )
    await session.commit()
    return project.id, "CHAR_001"


@pytest.mark.asyncio
async def test_get_and_save_character_roundtrip(session) -> None:
    _, character_id = await _character(session)
    repo = SQLAlchemyCharacterCastingRepository(session)

    character = await repo.get_character(character_id)
    assert character is not None
    assert character.locked is False
    assert character.version == 1

    character.visual_identity_id = "asset-root"
    character.reference_pack = {"front": "asset-front"}
    character.locked = True
    saved = await repo.save_character(character)
    await session.commit()

    assert saved.visual_identity_id == "asset-root"
    assert saved.reference_pack == {"front": "asset-front"}
    assert saved.locked is True

    refetched = await repo.get_character(character_id)
    assert refetched.reference_pack == {"front": "asset-front"}


@pytest.mark.asyncio
async def test_save_character_raises_for_unknown_character(session) -> None:
    repo = SQLAlchemyCharacterCastingRepository(session)
    with pytest.raises(ValueError):
        await repo.save_character(Character(id="does-not-exist", name="Ghost", role="extra"))


@pytest.mark.asyncio
async def test_set_lock_and_unlock_and_bump_version(session) -> None:
    _, character_id = await _character(session)
    repo = SQLAlchemyCharacterCastingRepository(session)

    locked = await repo.set_lock(character_id, True)
    assert locked.locked is True
    assert locked.version == 1

    unlocked = await repo.unlock_and_bump_version(character_id)
    await session.commit()
    assert unlocked.locked is False
    assert unlocked.version == 2


@pytest.mark.asyncio
async def test_wardrobe_variant_crud(session) -> None:
    _, character_id = await _character(session)
    repo = SQLAlchemyCharacterCastingRepository(session)

    created = await repo.create_wardrobe_variant(
        character_id, "office_black_dress", ["asset-1"], description="pilot episode outfit"
    )
    await session.commit()
    assert created.character_id == character_id

    variants = await repo.list_wardrobe_variants(character_id)
    assert len(variants) == 1
    assert variants[0].label == "office_black_dress"


@pytest.mark.asyncio
async def test_physical_state_variant_crud(session) -> None:
    _, character_id = await _character(session)
    repo = SQLAlchemyCharacterCastingRepository(session)

    await repo.create_physical_state_variant(character_id, "injured", ["asset-2"])
    await session.commit()

    variants = await repo.list_physical_state_variants(character_id)
    assert len(variants) == 1
    assert variants[0].label == "injured"


@pytest.mark.asyncio
async def test_asset_list_by_ownership_filters_by_character_id(session) -> None:
    project_id, character_id = await _character(session)
    asset_repo = SQLAlchemyAssetRepository(session)
    await asset_repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="a.png",
        content_hash="h1",
        ownership=AssetOwnership(project_id=project_id, character_id=character_id),
    )
    await asset_repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="b.png",
        content_hash="h2",
        ownership=AssetOwnership(project_id=project_id),
    )
    await session.commit()

    only_character = await asset_repo.list_by_ownership(project_id, character_id=character_id)
    assert [a.storage_path for a in only_character] == ["a.png"]

    all_for_project = await asset_repo.list_by_ownership(project_id)
    assert len(all_for_project) == 2
