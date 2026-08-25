"""Human feedback service (MODULE-065).

Denormalizes `provider`/`model` from the asset's provenance at feedback
time - "link feedback to exact artifact/take/version/model" without
requiring every reader to join back through `Asset`.
"""

from xerama.domain.feedback import HumanFeedback
from xerama.repositories.interfaces import AssetRepository, HumanFeedbackRepository


class HumanFeedbackService:
    def __init__(self, repo: HumanFeedbackRepository, asset_repo: AssetRepository) -> None:
        self._repo = repo
        self._asset_repo = asset_repo

    async def record(
        self,
        asset_id: str,
        decision: str,
        reason: str = "",
        rating: int | None = None,
        tags: list[str] | None = None,
        reviewer: str = "",
    ) -> HumanFeedback:
        asset = await self._asset_repo.get(asset_id)
        if asset is None:
            raise ValueError(f"asset {asset_id} not found")
        return await self._repo.create(
            asset_id=asset_id,
            decision=decision,
            project_id=asset.ownership.project_id,
            reason=reason,
            rating=rating,
            tags=tags,
            reviewer=reviewer,
            provider=asset.provenance.provider,
            model=asset.provenance.model,
        )

    async def list_by_asset(self, asset_id: str) -> list[HumanFeedback]:
        return await self._repo.list_by_asset(asset_id)

    async def list_by_project(self, project_id: str) -> list[HumanFeedback]:
        return await self._repo.list_by_project(project_id)
