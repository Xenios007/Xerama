"""Provider ranking / optimization recommendations service (MODULE-064)."""

from xerama.domain.asset import AssetStatus
from xerama.pipeline.provider_ranking import Objective, ProviderRanking, rank_providers
from xerama.repositories.interfaces import AssetRepository, CostRecordRepository, MediaQCRepository


class OptimizationService:
    def __init__(
        self,
        cost_repo: CostRecordRepository,
        qc_repo: MediaQCRepository,
        asset_repo: AssetRepository,
    ) -> None:
        self._cost_repo = cost_repo
        self._qc_repo = qc_repo
        self._asset_repo = asset_repo

    async def rank_providers(self, project_id: str, objective: Objective = "balanced") -> list[ProviderRanking]:
        cost_records = await self._cost_repo.list_by_project(project_id)
        asset_ids = sorted({r.asset_id for r in cost_records if r.asset_id})

        accepted_assets = await self._asset_repo.list_by_ownership(project_id, status=AssetStatus.ACCEPTED)
        accepted_asset_ids = {a.id for a in accepted_assets}

        qc_attempts = await self._qc_repo.list_by_assets(asset_ids)
        scores_by_asset: dict[str, list[float]] = {}
        for attempt in qc_attempts:
            scores_by_asset.setdefault(attempt.asset_id, []).append(attempt.score)
        qc_scores_by_asset = {
            asset_id: sum(scores) / len(scores) for asset_id, scores in scores_by_asset.items()
        }

        return rank_providers(cost_records, accepted_asset_ids, qc_scores_by_asset, objective)
