from xerama.domain.asset import Asset, AssetOwnership, AssetStatus, AssetType


def test_asset_defaults() -> None:
    asset = Asset(
        id="ASSET_1",
        type=AssetType.IMAGE,
        storage_path="ab/abc.png",
        content_hash="abc",
        ownership=AssetOwnership(project_id="PROJ_1"),
    )
    assert asset.status == AssetStatus.PENDING
    assert asset.take_number == 1
    assert asset.rejection_reason == ""
    assert asset.provenance.provider == ""
    assert asset.ownership.series_id is None


def test_asset_round_trip() -> None:
    asset = Asset(
        id="ASSET_1",
        type=AssetType.VIDEO,
        status=AssetStatus.ACCEPTED,
        storage_path="ab/abc.mp4",
        content_hash="abc",
        ownership=AssetOwnership(project_id="PROJ_1", episode_id="EP_1", shot_number=3),
    )
    restored = Asset.model_validate_json(asset.model_dump_json())
    assert restored.ownership.shot_number == 3
    assert restored.status == AssetStatus.ACCEPTED
