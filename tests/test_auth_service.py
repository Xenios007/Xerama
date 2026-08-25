import pytest

from xerama.domain.enums import ProjectRole
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAuthSessionRepository,
    SQLAlchemyProjectMembershipRepository,
    SQLAlchemyUserRepository,
)
from xerama.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)


def _service(session) -> AuthService:
    return AuthService(
        user_repo=SQLAlchemyUserRepository(session),
        session_repo=SQLAlchemyAuthSessionRepository(session),
        membership_repo=SQLAlchemyProjectMembershipRepository(session),
    )


async def test_register_hashes_password_not_plaintext(session) -> None:
    service = _service(session)
    user = await service.register("alice@example.com", "correct horse battery")
    await session.commit()

    assert user.password_hash != "correct horse battery"
    assert "correct horse battery" not in user.password_hash


async def test_register_normalizes_email_to_lowercase(session) -> None:
    service = _service(session)
    user = await service.register("Alice@Example.COM", "correct horse battery")
    await session.commit()

    assert user.email == "alice@example.com"


async def test_register_rejects_malformed_email(session) -> None:
    service = _service(session)
    with pytest.raises(ValueError):
        await service.register("not-an-email", "correct horse battery")


async def test_register_rejects_short_password(session) -> None:
    service = _service(session)
    with pytest.raises(ValueError):
        await service.register("alice@example.com", "short")


async def test_register_rejects_duplicate_email(session) -> None:
    service = _service(session)
    await service.register("alice@example.com", "correct horse battery")
    await session.commit()

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register("alice@example.com", "another password")


async def test_login_succeeds_with_correct_password(session) -> None:
    service = _service(session)
    await service.register("alice@example.com", "correct horse battery")
    await session.commit()

    user, auth_session = await service.login("alice@example.com", "correct horse battery")
    await session.commit()

    assert user.email == "alice@example.com"
    assert auth_session.token
    assert auth_session.user_id == user.id


async def test_login_rejects_wrong_password(session) -> None:
    service = _service(session)
    await service.register("alice@example.com", "correct horse battery")
    await session.commit()

    with pytest.raises(InvalidCredentialsError):
        await service.login("alice@example.com", "wrong password")


async def test_login_rejects_unknown_email(session) -> None:
    service = _service(session)
    with pytest.raises(InvalidCredentialsError):
        await service.login("nobody@example.com", "whatever password")


async def test_get_user_for_token_round_trips(session) -> None:
    service = _service(session)
    await service.register("alice@example.com", "correct horse battery")
    await session.commit()
    _, auth_session = await service.login("alice@example.com", "correct horse battery")
    await session.commit()

    resolved = await service.get_user_for_token(auth_session.token)
    assert resolved is not None
    assert resolved.email == "alice@example.com"


async def test_get_user_for_token_returns_none_for_unknown_token(session) -> None:
    service = _service(session)
    assert await service.get_user_for_token("not-a-real-token") is None


async def test_logout_invalidates_the_session_token(session) -> None:
    service = _service(session)
    await service.register("alice@example.com", "correct horse battery")
    await session.commit()
    _, auth_session = await service.login("alice@example.com", "correct horse battery")
    await session.commit()

    await service.logout(auth_session.token)
    await session.commit()

    assert await service.get_user_for_token(auth_session.token) is None


async def test_grant_project_role_is_idempotent_per_user_and_project(session) -> None:
    service = _service(session)
    user = await service.register("alice@example.com", "correct horse battery")
    await session.commit()

    first = await service.grant_project_role("P1", user.id, ProjectRole.VIEWER)
    await session.commit()
    second = await service.grant_project_role("P1", user.id, ProjectRole.OWNER)
    await session.commit()

    assert first.id == second.id  # same membership row, role updated in place
    assert second.role == ProjectRole.OWNER
