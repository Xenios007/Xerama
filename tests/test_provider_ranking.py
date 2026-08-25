from xerama.domain.cost import CostRecord
from xerama.pipeline.provider_ranking import rank_providers


def _record(**overrides) -> CostRecord:
    fields = dict(
        id="R1", provider="reliable", model="m", stage="image_generation",
        unit="images", quantity=1.0, attempt=1,
    )
    fields.update(overrides)
    return CostRecord(**fields)


def test_rank_providers_orders_by_composite_score() -> None:
    records = [
        _record(id="R1", provider="reliable", asset_id="A1", cost_usd=0.01, cost_known=True, latency_ms=500),
        _record(id="R2", provider="flaky", asset_id="A2", cost_usd=0.01, cost_known=True, latency_ms=500),
    ]
    rankings = rank_providers(records, accepted_asset_ids={"A1"}, qc_scores_by_asset={}, objective="balanced")
    by_provider = {r.provider: r for r in rankings}
    assert by_provider["reliable"].accepted_rate == 1.0
    assert by_provider["flaky"].accepted_rate == 0.0
    assert rankings[0].provider == "reliable"  # higher composite score first


def test_rank_providers_groups_by_provider_and_stage() -> None:
    records = [
        _record(id="R1", provider="p", stage="image_generation", asset_id="A1"),
        _record(id="R2", provider="p", stage="video_generation", asset_id="A2"),
    ]
    rankings = rank_providers(records, accepted_asset_ids=set(), qc_scores_by_asset={})
    stages = {r.stage for r in rankings}
    assert stages == {"image_generation", "video_generation"}


def test_rank_providers_excludes_unknown_cost_from_average() -> None:
    records = [
        _record(id="R1", provider="p", asset_id="A1", cost_usd=None, cost_known=False),
        _record(id="R2", provider="p", asset_id="A2", cost_usd=0.02, cost_known=True),
    ]
    rankings = rank_providers(records, accepted_asset_ids=set(), qc_scores_by_asset={})
    assert rankings[0].avg_cost_usd == 0.02
    assert rankings[0].sample_count == 2


def test_rank_providers_incorporates_qc_score() -> None:
    records = [_record(id="R1", provider="p", asset_id="A1")]
    quality_focused = rank_providers(
        records, accepted_asset_ids=set(), qc_scores_by_asset={"A1": 9.0}, objective="quality"
    )
    assert quality_focused[0].avg_qc_score == 9.0
    assert quality_focused[0].composite_score > 0.5  # high QC dominates under the "quality" objective


def test_rank_providers_objective_changes_ranking() -> None:
    records = [
        _record(id="R1", provider="cheap_slow", asset_id="A1", cost_usd=0.001, cost_known=True, latency_ms=60000),
        _record(id="R2", provider="pricey_fast", asset_id="A2", cost_usd=1.0, cost_known=True, latency_ms=100),
    ]
    accepted = {"A1", "A2"}
    budget_ranking = rank_providers(records, accepted, {}, objective="budget")
    speed_ranking = rank_providers(records, accepted, {}, objective="speed")
    assert budget_ranking[0].provider == "cheap_slow"
    assert speed_ranking[0].provider == "pricey_fast"


def test_rank_providers_ignores_records_with_no_provider() -> None:
    records = [_record(id="R1", provider="", asset_id="A1")]
    assert rank_providers(records, set(), {}) == []
