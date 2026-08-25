"""Production cost recording service (MODULE-049).

The one place that persists a `CostRecord`. Kept deliberately dumb (a
thin wrapper over the repository) - callers (the AI gateway, media
production services) decide what to record; this only writes it down.
"""

from xerama.domain.asset import Asset
from xerama.domain.cost import CostRecord
from xerama.repositories.interfaces import CostRecordRepository


class CostRecordService:
    def __init__(self, repo: CostRecordRepository) -> None:
        self._repo = repo

    async def record(
        self,
        provider: str,
        model: str,
        stage: str,
        project_id: str | None = None,
        series_id: str | None = None,
        episode_id: str | None = None,
        scene_number: int | None = None,
        shot_number: int | None = None,
        attempt: int = 1,
        quantity: float = 0.0,
        unit: str = "",
        cost_usd: float | None = None,
        cost_known: bool = False,
        latency_ms: float | None = None,
        asset_id: str | None = None,
        failure_reason: str = "",
    ) -> CostRecord:
        return await self._repo.create(
            provider=provider,
            model=model,
            stage=stage,
            project_id=project_id,
            series_id=series_id,
            episode_id=episode_id,
            scene_number=scene_number,
            shot_number=shot_number,
            attempt=attempt,
            quantity=quantity,
            unit=unit,
            cost_usd=cost_usd,
            cost_known=cost_known,
            latency_ms=latency_ms,
            asset_id=asset_id,
            failure_reason=failure_reason,
        )

    async def list_by_project(self, project_id: str) -> list[CostRecord]:
        return await self._repo.list_by_project(project_id)

    async def list_by_episode(self, episode_id: str) -> list[CostRecord]:
        return await self._repo.list_by_episode(episode_id)

    async def record_generation_attempts(
        self,
        asset: Asset,
        stage: str,
        project_id: str | None = None,
        series_id: str | None = None,
        episode_id: str | None = None,
        scene_number: int | None = None,
        shot_number: int | None = None,
        quantity: float = 0.0,
        unit: str = "",
    ) -> None:
        """One `CostRecord` per `MediaProviderRouter` routing attempt
        recorded in `asset.provenance.generation_params["routing_attempts"]`
        (Module 07) - every non-winning attempt still cost a call (ADR-024
        "incorporating retries"), so it's recorded as a zero-quantity
        failure, not silently dropped. Deliberately reads what
        `StoryboardService`/`VideoProductionService`/`AudioProductionService`
        already persist rather than requiring those services to take a new
        constructor dependency - keeps this fully additive at the API
        layer, with zero blast radius on their existing tests."""
        attempts = asset.provenance.generation_params.get("routing_attempts", [])
        for attempt in attempts:
            outcome = attempt.get("outcome", "")
            if outcome == "selected":
                await self.record(
                    provider=attempt.get("provider_name", asset.provenance.provider),
                    model=asset.provenance.model,
                    stage=stage,
                    project_id=project_id,
                    series_id=series_id,
                    episode_id=episode_id,
                    scene_number=scene_number,
                    shot_number=shot_number,
                    quantity=quantity,
                    unit=unit,
                    cost_known=False,
                    asset_id=asset.id,
                )
            else:
                await self.record(
                    provider=attempt.get("provider_name", ""),
                    model="",
                    stage=stage,
                    project_id=project_id,
                    series_id=series_id,
                    episode_id=episode_id,
                    scene_number=scene_number,
                    shot_number=shot_number,
                    unit=unit,
                    cost_known=False,
                    failure_reason=f"{outcome}: {attempt.get('detail', '')}".strip(": "),
                )
        if not attempts:
            # Manual upload or another path with no router attempts to
            # replay - still record the winning attempt itself.
            await self.record(
                provider=asset.provenance.provider,
                model=asset.provenance.model,
                stage=stage,
                project_id=project_id,
                series_id=series_id,
                episode_id=episode_id,
                scene_number=scene_number,
                shot_number=shot_number,
                quantity=quantity,
                unit=unit,
                cost_known=False,
                asset_id=asset.id,
            )
