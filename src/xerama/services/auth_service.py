"""Authentication service (MODULE-067).

Password hashing uses `hashlib.scrypt` - a standard-library, memory-hard
KDF designed specifically to resist brute-force password cracking, never
a hand-rolled hash. Session tokens are opaque, cryptographically random
strings (`secrets.token_urlsafe`), not a signed/encoded format (JWT
etc.) - "avoid building custom cryptography" is satisfied by using only
well-audited stdlib primitives and never inventing a token format.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from xerama.domain.auth import AuthSession, ProjectMembership, User
from xerama.domain.enums import ProjectRole
from xerama.repositories.interfaces import (
    AuthSessionRepository,
    ProjectMembershipRepository,
    UserRepository,
)

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LENGTH = 8
# scrypt cost parameters - N=2**14 is the interactive-login-friendly
# baseline recommended by RFC 7914 for browser/API-latency contexts.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DEFAULT_SESSION_TTL = timedelta(hours=24)


class InvalidCredentialsError(ValueError):
    pass


class EmailAlreadyRegisteredError(ValueError):
    pass


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"{salt.hex()}${derived.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, derived_hex = password_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(derived_hex)
    except ValueError:
        return False
    candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return hmac.compare_digest(candidate, expected)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: AuthSessionRepository,
        membership_repo: ProjectMembershipRepository,
        session_ttl: timedelta = _DEFAULT_SESSION_TTL,
    ) -> None:
        self._user_repo = user_repo
        self._session_repo = session_repo
        self._membership_repo = membership_repo
        self._session_ttl = session_ttl

    async def register(self, email: str, password: str, display_name: str = "") -> User:
        normalized_email = email.strip().lower()
        if not _EMAIL_PATTERN.match(normalized_email):
            raise ValueError(f"invalid email address: {email!r}")
        if len(password) < _MIN_PASSWORD_LENGTH:
            raise ValueError(f"password must be at least {_MIN_PASSWORD_LENGTH} characters")
        if await self._user_repo.get_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError(f"{normalized_email} is already registered")
        return await self._user_repo.create(
            email=normalized_email,
            password_hash=_hash_password(password),
            display_name=display_name,
        )

    async def login(self, email: str, password: str) -> tuple[User, AuthSession]:
        normalized_email = email.strip().lower()
        user = await self._user_repo.get_by_email(normalized_email)
        if user is None or not _verify_password(password, user.password_hash):
            raise InvalidCredentialsError("invalid email or password")
        expires_at = datetime.now(timezone.utc) + self._session_ttl
        token = secrets.token_urlsafe(32)
        session = await self._session_repo.create(user_id=user.id, token=token, expires_at=expires_at)
        return user, session

    async def logout(self, token: str) -> None:
        await self._session_repo.delete_by_token(token)

    async def get_user_for_token(self, token: str) -> User | None:
        session = await self._session_repo.get_by_token(token)
        if session is None or session.expires_at < datetime.now(timezone.utc):
            return None
        return await self._user_repo.get(session.user_id)

    async def grant_project_role(
        self, project_id: str, user_id: str, role: ProjectRole
    ) -> ProjectMembership:
        return await self._membership_repo.grant(project_id=project_id, user_id=user_id, role=role)
