import pytest

from xerama.domain.character import CharacterDNA, CharacterProvenance
from xerama.domain.enums import IdentityType
from xerama.repositories.sqlalchemy_impl import SQLAlchemyCharacterCastingRepository
from xerama.services.character_casting_service import CharacterCastingService

from test_character_casting_repository import _character


def _service(session) -> CharacterCastingService:
    return CharacterCastingService(repo=SQLAlchemyCharacterCastingRepository(session))


async def test_get_unknown_character_raises(session) -> None:
    service = _service(session)
    with pytest.raises(ValueError):
        await service.get("does-not-exist")


async def test_update_identity_when_unlocked(session) -> None:
    _, character_id = await _character(session)
    service = _service(session)

    updated = await service.update_identity(
        character_id,
        visual_identity_id="asset-root",
        reference_pack_updates={"front": "asset-front"},
        character_dna=CharacterDNA(eyes="green"),
    )
    await session.commit()

    assert updated.visual_identity_id == "asset-root"
    assert updated.reference_pack == {"front": "asset-front"}
    assert updated.character_dna.eyes == "green"


async def test_locked_identity_is_immutable(session) -> None:
    _, character_id = await _character(session)
    service = _service(session)

    await service.lock(character_id)
    await session.commit()

    with pytest.raises(PermissionError):
        await service.update_identity(character_id, visual_identity_id="asset-root")

    with pytest.raises(PermissionError):
        await service.set_provenance(
            character_id,
            CharacterProvenance(identity_type=IdentityType.LICENSED_AUTHORIZED, consent_reference="LIC-1"),
        )


async def test_unlock_for_recast_allows_update_and_bumps_version(session) -> None:
    _, character_id = await _character(session)
    service = _service(session)

    await service.lock(character_id)
    await session.commit()

    recast = await service.unlock_for_recast(character_id)
    await session.commit()
    assert recast.locked is False
    assert recast.version == 2

    updated = await service.update_identity(character_id, visual_identity_id="asset-root-v2")
    await session.commit()
    assert updated.visual_identity_id == "asset-root-v2"
    assert updated.version == 2


async def test_wardrobe_and_physical_state_additions_allowed_while_locked(session) -> None:
    _, character_id = await _character(session)
    service = _service(session)

    await service.lock(character_id)
    await session.commit()

    wardrobe = await service.add_wardrobe_variant(character_id, "hospital_gown", ["asset-w1"])
    state = await service.add_physical_state_variant(character_id, "injured", ["asset-s1"])
    await session.commit()

    assert wardrobe.label == "hospital_gown"
    assert state.label == "injured"
    assert [v.label for v in await service.list_wardrobe_variants(character_id)] == ["hospital_gown"]
    assert [v.label for v in await service.list_physical_state_variants(character_id)] == ["injured"]


async def test_add_wardrobe_variant_404s_for_unknown_character(session) -> None:
    service = _service(session)
    with pytest.raises(ValueError):
        await service.add_wardrobe_variant("does-not-exist", "label")
