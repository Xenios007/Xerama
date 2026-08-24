"""Local CLI entrypoint for running the full XER-001 pipeline without a
server - `python -m xerama.cli --genre "..." --premise "..."`.

Exercises the same Showrunner/repositories/AIGateway construction as the API
so a Trial 01 run can be driven from a terminal.
"""

import argparse
import asyncio
import json
import logging

import httpx

from xerama.config import ModelRoleRegistry, get_settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.domain.brief import CreativeBrief
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.orchestrator import Showrunner
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.openrouter import OpenRouterProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyConceptRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeasonRepository,
    SQLAlchemySeriesRepository,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Xerama XER-001 story pipeline locally.")
    parser.add_argument("--name", default="Trial 01", help="Project name")
    parser.add_argument("--genre", required=True)
    parser.add_argument("--premise", default="")
    parser.add_argument("--target-audience", default="general")
    parser.add_argument("--episode-count", type=int, default=3)
    parser.add_argument("--episode-duration", type=int, default=75)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    engine = make_engine(settings.database_url)
    await create_all(engine)
    session_factory = make_session_factory(engine)

    async with httpx.AsyncClient(timeout=120.0) as http_client:
        provider = OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            http_client=http_client,
        )
        gateway = AIGateway(
            provider=provider, roles=ModelRoleRegistry(settings), health=ProviderHealthTracker()
        )

        async with session_factory() as session:
            project_repo = SQLAlchemyProjectRepository(session)
            project = await project_repo.create(args.name)
            await session.commit()

            showrunner = Showrunner(
                gateway=gateway,
                concept_repo=SQLAlchemyConceptRepository(session),
                series_repo=SQLAlchemySeriesRepository(session),
                season_repo=SQLAlchemySeasonRepository(session),
                episode_repo=SQLAlchemyEpisodeRepository(session),
                job_repo=SQLAlchemyJobRepository(session),
            )
            brief = CreativeBrief(
                genre=args.genre,
                premise=args.premise,
                target_audience=args.target_audience,
                episode_count=args.episode_count,
                episode_duration_seconds=args.episode_duration,
            )
            result = await showrunner.run(project.id, brief)
            await session.commit()

    print(result.model_dump_json(indent=2))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
