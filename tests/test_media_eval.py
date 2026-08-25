from xerama.domain.asset import AssetType
from xerama.domain.enums import ShotClass
from xerama.domain.media_eval import MediaEvalRunResult
from xerama.eval.media_datasets import (
    IMAGE_CASES,
    SHOT_CLASS_QC_DIMENSIONS,
    VIDEO_CASES,
    cases_for_asset_type,
)
from xerama.pipeline.media_eval_aggregation import summarize_by_shot_class


# --- dataset (MODULE-073) -------------------------------------------------


def test_cases_for_asset_type_returns_image_cases() -> None:
    assert cases_for_asset_type(AssetType.IMAGE) == IMAGE_CASES


def test_cases_for_asset_type_returns_video_cases() -> None:
    assert cases_for_asset_type(AssetType.VIDEO) == VIDEO_CASES


def test_image_dataset_covers_every_shot_class() -> None:
    """"Curated test shots covering identity, dialogue, motion,
    establishing and multi-character cases" - the five shot classes must
    all appear somewhere across the two datasets."""
    covered = {c.shot_class for c in IMAGE_CASES} | {c.shot_class for c in VIDEO_CASES}
    assert covered == set(ShotClass)


def test_every_shot_class_has_at_least_one_qc_dimension() -> None:
    for shot_class in ShotClass:
        assert len(SHOT_CLASS_QC_DIMENSIONS[shot_class]) >= 1


def test_every_case_has_a_unique_id() -> None:
    all_cases = IMAGE_CASES + VIDEO_CASES
    ids = [c.id for c in all_cases]
    assert len(ids) == len(set(ids))


def test_establishing_shots_need_no_reference_images() -> None:
    establishing = [c for c in IMAGE_CASES if c.shot_class == ShotClass.ESTABLISHING]
    assert establishing
    assert all(c.reference_image_count == 0 for c in establishing)


def test_identity_and_multi_character_shots_carry_reference_images() -> None:
    for c in IMAGE_CASES:
        if c.shot_class in (ShotClass.IDENTITY, ShotClass.MULTI_CHARACTER):
            assert c.reference_image_count >= 1


# --- aggregation -----------------------------------------------------------


def _result(**overrides) -> MediaEvalRunResult:
    fields = dict(
        id="R1", case_id="c1", shot_class=ShotClass.IDENTITY, asset_type=AssetType.IMAGE,
        dataset_version="v1", provider="fake_image", generation_succeeded=True, attempts=1,
        latency_ms=50.0, estimated_cost_usd=0.01, accepted=True,
    )
    fields.update(overrides)
    return MediaEvalRunResult(**fields)


def test_summarize_by_shot_class_groups_by_shot_class_and_provider() -> None:
    results = [
        _result(id="R1", shot_class=ShotClass.IDENTITY, provider="p1"),
        _result(id="R2", shot_class=ShotClass.IDENTITY, provider="p2"),
        _result(id="R3", shot_class=ShotClass.MOTION, provider="p1"),
    ]
    benchmarks = summarize_by_shot_class(results)
    keys = {(b.shot_class, b.provider) for b in benchmarks}
    assert keys == {
        (ShotClass.IDENTITY, "p1"), (ShotClass.IDENTITY, "p2"), (ShotClass.MOTION, "p1")
    }


def test_summarize_by_shot_class_never_averages_across_shot_classes() -> None:
    results = [
        _result(id="R1", shot_class=ShotClass.IDENTITY, provider="p1", accepted=True, estimated_cost_usd=1.0),
        _result(id="R2", shot_class=ShotClass.MOTION, provider="p1", accepted=False, estimated_cost_usd=1.0),
    ]
    benchmarks = summarize_by_shot_class(results)
    assert len(benchmarks) == 2
    identity_row = next(b for b in benchmarks if b.shot_class == ShotClass.IDENTITY)
    motion_row = next(b for b in benchmarks if b.shot_class == ShotClass.MOTION)
    assert identity_row.acceptance_rate == 1.0
    assert motion_row.acceptance_rate == 0.0


def test_summarize_by_shot_class_computes_cost_per_accepted() -> None:
    results = [
        _result(id="R1", accepted=True, estimated_cost_usd=1.0),
        _result(id="R2", accepted=False, estimated_cost_usd=1.0),  # a wasted attempt still costs
    ]
    benchmarks = summarize_by_shot_class(results)
    assert len(benchmarks) == 1
    # numerator = 1.0 + 1.0 = 2.0, denominator = 1 accepted -> 2.0/accepted
    assert benchmarks[0].estimated_cost_per_accepted_usd == 2.0


def test_summarize_by_shot_class_never_fabricates_cost_when_nothing_accepted() -> None:
    results = [_result(id="R1", accepted=False)]
    benchmarks = summarize_by_shot_class(results)
    assert benchmarks[0].estimated_cost_per_accepted_usd is None


def test_summarize_by_shot_class_ignores_runs_with_no_provider() -> None:
    """A run that failed before any provider was selected has nothing to
    attribute a benchmark row to."""
    results = [_result(id="R1", provider="", generation_succeeded=False, accepted=False)]
    assert summarize_by_shot_class(results) == []
