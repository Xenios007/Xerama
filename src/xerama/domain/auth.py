"""Identity/authorization domain contracts (MODULE-067).

"Keep local single-user mode simple but design the auth boundary
explicitly" - these models exist unconditionally, but enforcement only
activates when `Settings.xerama_mode == "hosted"` (see
`api/authorization.py`). In the default "standard" (local single-user)
mode, no `User`/`Session`/`ProjectMembership` row is ever required to
exist for the app to function - see ADR-free reasoning in
docs/IMPLEMENTATION_STATUS.md MODULE-067.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from xerama.domain.enums import ProjectRole


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class User(BaseModel):
    id: str
    # A plain `str`, not pydantic's `EmailStr` - that requires the
    # optional `email-validator` package, which is not in this project's
    # minimal dependency set (see pyproject.toml). Format is validated in
    # `services/auth_service.py` at registration time instead.
    email: str
    # Never the plaintext password - see services/auth_service.py
    # (hashlib.scrypt, a standard-library, audited primitive - "avoid
    # building custom cryptography").
    password_hash: str
    display_name: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class AuthSession(BaseModel):
    """An opaque bearer-token session - not a JWT, so there is no custom
    token-signing/verification logic to get wrong (again, "avoid building
    custom cryptography"); validity is a straight DB lookup + expiry
    check, the same trust model as e.g. Django's session framework."""

    id: str
    user_id: str
    token: str
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime


class ProjectMembership(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: ProjectRole
    created_at: datetime = Field(default_factory=_utcnow)
