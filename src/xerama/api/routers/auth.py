"""Registration/login/logout endpoints (MODULE-067).

Exists and works in every `xerama_mode`, but only matters once a
deployment sets `xerama_mode=hosted` - see `api/authorization.py`. In
"standard" (local single-user) mode nothing in the rest of the API ever
requires a session token.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from xerama.api.authorization import get_current_user
from xerama.domain.auth import User
from xerama.services.auth_service import AuthService, EmailAlreadyRegisteredError, InvalidCredentialsError

from xerama.api.deps import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class PublicUser(BaseModel):
    id: str
    email: str
    display_name: str

    @classmethod
    def from_user(cls, user: User) -> "PublicUser":
        return cls(id=user.id, email=user.email, display_name=user.display_name)


class LoginResponse(BaseModel):
    token: str
    user: PublicUser


@router.post("/register", response_model=PublicUser)
async def register(
    payload: RegisterRequest, service: AuthService = Depends(get_auth_service)
) -> PublicUser:
    try:
        user = await service.register(payload.email, payload.password, payload.display_name)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PublicUser.from_user(user)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> LoginResponse:
    try:
        user, session = await service.login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return LoginResponse(token=session.token, user=PublicUser.from_user(user))


@router.post("/logout", status_code=204)
async def logout(request: Request, service: AuthService = Depends(get_auth_service)) -> None:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        await service.logout(auth_header[7:].strip())


@router.get("/me", response_model=PublicUser)
async def get_me(user: User | None = Depends(get_current_user)) -> PublicUser:
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return PublicUser.from_user(user)
