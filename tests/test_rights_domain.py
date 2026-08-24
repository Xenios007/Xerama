from xerama.domain.rights import RightsMetadata


def test_empty_license_type_is_not_known() -> None:
    assert RightsMetadata().is_known is False


def test_unknown_license_type_is_not_known() -> None:
    assert RightsMetadata(license_type="unknown").is_known is False


def test_royalty_free_license_is_known() -> None:
    assert RightsMetadata(license_type="royalty_free").is_known is True


def test_licensed_with_reference_is_known() -> None:
    rights = RightsMetadata(
        source="library",
        license_type="licensed",
        rights_owner="Acme Music Co",
        license_reference="LIC-2026-001",
    )
    assert rights.is_known is True
