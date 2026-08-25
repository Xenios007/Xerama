"""Server-side project-ownership enforcement (MODULE-067).

"Keep local single-user mode simple but design the auth boundary
explicitly": `authorize_project_access` is a no-op unless
`Settings.xerama_mode == "hosted"` - the default "standard" mode (all
564 pre-existing tests, and every current single-user deployment) never
calls a user/session/membership table at all. Hosted mode is where
"enforce authorization server-side on project/assets/jobs/reviews"
actually activates.

`require_project_role` is the `Depends`-friendly form for routers where
`project_id` is already a direct path/query parameter (assets, costs,
episodes, feedback, generation, health/observability, inspect, jobs,
optimization, projects itself). Routers that only resolve a project via
a child id (episode/storyboard/production/render) call
`authorize_project_access` directly once they have resolved
`project_id` - see `shot_lookup.episode_context`, which every one of
those routers already uses to look up the owning series.
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.api.deps import get_character_casting_repo, get_episode_repo, get_series_repo, get_session
from xerama.config import get_settings
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.repositories.interfaces import (
    CharacterCastingRepository,
    EpisodeRepository,
    ProjectMembershipRepository,
    SeriesRepository,
)
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAuthSessionRepository,
    SQLAlchemyProjectMembershipRepository,
    SQLAlchemyUserRepository,
)

_ROLE_RANK = {ProjectRole.VIEWER: 0, ProjectRole.EDITOR: 1, ProjectRole.OWNER: 2}


def _role_at_least(actual: ProjectRole, required: ProjectRole) -> bool:
    return _ROLE_RANK[actual] >= _ROLE_RANK[required]


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Resolves the caller from `Authorization: Bearer <token>`. Never
    raises - callers that require a user check for `None` themselves, so
    the same dependency works for both hosted-mode enforcement (where a
    missing user becomes a 401) and any future optional-auth read path."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None
    session_repo = SQLAlchemyAuthSessionRepository(session)
    record = await session_repo.get_by_token(token)
    if record is None:
        return None
    if record.expires_at < datetime.now(timezone.utc):
        return None
    user_repo = SQLAlchemyUserRepository(session)
    return await user_repo.get(record.user_id)


def get_project_membership_repo(
    session: AsyncSession = Depends(get_session),
) -> SQLAlchemyProjectMembershipRepository:
    return SQLAlchemyProjectMembershipRepository(session)


async def authorize_project_access(
    project_id: str,
    min_role: ProjectRole,
    user: User | None,
    membership_repo: ProjectMembershipRepository,
) -> None:
    """Raises `HTTPException` if the current request may not touch
    `project_id` at `min_role` or above. A no-op in "standard" mode."""
    settings = get_settings()
    if settings.xerama_mode != "hosted":
        return
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    membership = await membership_repo.get(project_id, user.id)
    if membership is None or not _role_at_least(membership.role, min_role):
        raise HTTPException(status_code=403, detail="insufficient project role")


def require_project_role(min_role: ProjectRole):
    """`Depends()`-compatible factory for routers where `project_id` is
    already a path/query parameter of the endpoint it decorates."""

    async def _check(
        project_id: str,
        user: User | None = Depends(get_current_user),
        membership_repo: SQLAlchemyProjectMembershipRepository = Depends(get_project_membership_repo),
    ) -> None:
        await authorize_project_access(project_id, min_role, user, membership_repo)

    return _check


def require_series_role(min_role: ProjectRole):
    """`Depends()`-compatible factory for routers where `series_id` is
    already a path parameter - resolves to the owning project via
    `SeriesRepository.get_series` (every `SeriesRecord` carries
    `project_id` directly)."""

    async def _check(
        series_id: str,
        user: User | None = Depends(get_current_user),
        membership_repo: SQLAlchemyProjectMembershipRepository = Depends(get_project_membership_repo),
        series_repo: SeriesRepository = Depends(get_series_repo),
    ) -> None:
        # Standard mode must be a true no-op - not even the extra
        # existence lookup below, which would otherwise turn a
        # downstream 409 ("no shot plan yet" etc.) into a 404 for a
        # request that used to reach the handler unauthorized-checked.
        if get_settings().xerama_mode != "hosted":
            return
        series = await series_repo.get_series(series_id)
        if series is None:
            raise HTTPException(status_code=404, detail="series not found")
        await authorize_project_access(series.project_id, min_role, user, membership_repo)

    return _check


def require_episode_role(min_role: ProjectRole):
    """`Depends()`-compatible factory for routers where `episode_id` is
    already a path parameter - resolves episode -> series -> project.
    Equivalent to calling `shot_lookup.episode_context(..., user=...,
    membership_repo=...)` and discarding the result; this form is for
    routers with no other use for the episode/series objects."""

    async def _check(
        episode_id: str,
        user: User | None = Depends(get_current_user),
        membership_repo: SQLAlchemyProjectMembershipRepository = Depends(get_project_membership_repo),
        episode_repo: EpisodeRepository = Depends(get_episode_repo),
        series_repo: SeriesRepository = Depends(get_series_repo),
    ) -> None:
        if get_settings().xerama_mode != "hosted":
            return
        episode = await episode_repo.get(episode_id)
        if episode is None:
            raise HTTPException(status_code=404, detail="episode not found")
        series = await series_repo.get_series(episode.series_id)
        if series is None:
            raise HTTPException(status_code=404, detail="series not found")
        await authorize_project_access(series.project_id, min_role, user, membership_repo)

    return _check


def require_character_role(min_role: ProjectRole):
    """`Depends()`-compatible factory for routers where `character_id` is
    already a path parameter - resolves character -> series -> project."""

    async def _check(
        character_id: str,
        user: User | None = Depends(get_current_user),
        membership_repo: SQLAlchemyProjectMembershipRepository = Depends(get_project_membership_repo),
        character_repo: CharacterCastingRepository = Depends(get_character_casting_repo),
        series_repo: SeriesRepository = Depends(get_series_repo),
    ) -> None:
        if get_settings().xerama_mode != "hosted":
            return
        series_id = await character_repo.get_character_series_id(character_id)
        if series_id is None:
            raise HTTPException(status_code=404, detail="character not found")
        series = await series_repo.get_series(series_id)
        if series is None:
            raise HTTPException(status_code=404, detail="series not found")
        await authorize_project_access(series.project_id, min_role, user, membership_repo)

    return _check
