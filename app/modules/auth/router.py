from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.email import EmailSender, get_email_sender
from app.modules.auth import service
from app.modules.auth.schemas import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
    VerifyRequest,
)
from app.modules.users.dependencies import RepoDep
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates an unverified user and sends a 6-digit verification code "
    "(printed to the console in development).",
)
async def signup(data: SignupRequest, repo: RepoDep, email_sender: EmailSenderDep) -> UserRead:
    user = await service.signup(repo, data, email_sender)
    return UserRead.model_validate(user)


@router.post(
    "/verify",
    response_model=UserRead,
    summary="Verify email",
    description="Confirms the 6-digit code sent at signup and marks the user as verified.",
)
async def verify(data: VerifyRequest, repo: RepoDep) -> UserRead:
    user = await service.verify(repo, data.email, data.code)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Log in",
    description="Validates credentials and returns an access/refresh JWT pair. "
    "Only verified users can log in.",
)
async def login(data: LoginRequest, repo: RepoDep) -> TokenPair:
    access, refresh_token = await service.login(repo, data.email, data.password)
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=AccessToken,
    summary="Refresh access token",
    description="Exchanges a valid refresh token for a new access token.",
)
async def refresh(data: RefreshRequest, repo: RepoDep) -> AccessToken:
    return AccessToken(access_token=await service.refresh(repo, data.refresh_token))
