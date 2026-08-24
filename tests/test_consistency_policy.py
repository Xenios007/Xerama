from xerama.domain.character import Character, PhysicalStateVariant, WardrobeVariant
from xerama.services.consistency_policy import ConsistencyPolicy


def _character(**overrides) -> Character:
    fields = {"id": "CHAR_001", "name": "Mara", "role": "protagonist"}
    fields.update(overrides)
    return Character(**fields)


def test_falls_back_to_character_id_when_no_identity_assets_exist() -> None:
    selection = ConsistencyPolicy().select_for_character(_character())
    assert selection.reference_asset_ids == ["CHAR_001"]


def test_prefers_root_identity_then_reference_pack_views_in_order() -> None:
    character = _character(
        visual_identity_id="asset-root",
        reference_pack={"side": "asset-side", "front": "asset-front", "full_body": "asset-body"},
    )
    selection = ConsistencyPolicy().select_for_character(character, max_references=10)
    # root first, then views in DEFAULT_VIEW_PREFERENCE order (front, three_quarter, side, full_body)
    assert selection.reference_asset_ids == ["asset-root", "asset-front", "asset-side", "asset-body"]


def test_wardrobe_and_physical_state_selection_appended() -> None:
    character = _character(visual_identity_id="asset-root")
    wardrobe = WardrobeVariant(
        id="W1", character_id="CHAR_001", label="hospital_gown", reference_asset_ids=["asset-w1"]
    )
    state = PhysicalStateVariant(
        id="S1", character_id="CHAR_001", label="injured", reference_asset_ids=["asset-s1"]
    )
    selection = ConsistencyPolicy().select_for_character(
        character, max_references=10, wardrobe_variant=wardrobe, physical_state_variant=state
    )
    assert selection.reference_asset_ids == ["asset-root", "asset-w1", "asset-s1"]
    assert selection.wardrobe_asset_ids == ["asset-w1"]
    assert selection.physical_state_asset_ids == ["asset-s1"]


def test_provider_max_reference_bound_truncates() -> None:
    character = _character(
        visual_identity_id="asset-root",
        reference_pack={"front": "asset-front", "three_quarter": "asset-3q", "side": "asset-side"},
    )
    selection = ConsistencyPolicy().select_for_character(character, max_references=2)
    assert selection.reference_asset_ids == ["asset-root", "asset-front"]
    assert len(selection.reference_asset_ids) == 2


def test_duplicate_asset_ids_are_deduped_preserving_order() -> None:
    character = _character(
        visual_identity_id="asset-root", reference_pack={"front": "asset-root"}  # same asset both slots
    )
    selection = ConsistencyPolicy().select_for_character(character, max_references=10)
    assert selection.reference_asset_ids == ["asset-root"]


def test_dna_text_uses_shared_formatter() -> None:
    from xerama.domain.character import format_character_dna

    character = _character(description="a tired detective")
    selection = ConsistencyPolicy().select_for_character(character)
    assert selection.dna_text == format_character_dna(character)


def test_multi_character_reference_selection_does_not_mix_characters() -> None:
    mara = _character(id="CHAR_001", name="Mara", visual_identity_id="asset-mara")
    lena = _character(id="CHAR_002", name="Lena", visual_identity_id="asset-lena")

    selections = ConsistencyPolicy().select_for_shot([mara, lena])

    by_id = {s.character_id: s for s in selections}
    assert by_id["CHAR_001"].reference_asset_ids == ["asset-mara"]
    assert by_id["CHAR_002"].reference_asset_ids == ["asset-lena"]
    assert "asset-lena" not in by_id["CHAR_001"].reference_asset_ids
    assert "asset-mara" not in by_id["CHAR_002"].reference_asset_ids


def test_multi_character_selection_applies_per_character_wardrobe() -> None:
    mara = _character(id="CHAR_001", name="Mara", visual_identity_id="asset-mara")
    lena = _character(id="CHAR_002", name="Lena", visual_identity_id="asset-lena")
    mara_wardrobe = WardrobeVariant(
        id="W1", character_id="CHAR_001", label="dress", reference_asset_ids=["asset-mara-dress"]
    )

    selections = ConsistencyPolicy().select_for_shot(
        [mara, lena], wardrobe_variants_by_character={"CHAR_001": mara_wardrobe}
    )
    by_id = {s.character_id: s for s in selections}
    assert "asset-mara-dress" in by_id["CHAR_001"].reference_asset_ids
    assert by_id["CHAR_002"].wardrobe_asset_ids == []
