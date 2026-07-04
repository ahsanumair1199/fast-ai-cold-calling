from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..schemas.auth import TokenOut, UserLogin, UserOut, UserRegister
from ..services.auth_service import authenticate_user, issue_token, register_user

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserRegister, session: AsyncSession = Depends(get_session)):
    user = await register_user(session, data)
    return user


@auth_router.post("/login", response_model=TokenOut)
async def login(data: UserLogin, session: AsyncSession = Depends(get_session)):
    user = await authenticate_user(session, data.email, data.password)
    return TokenOut(access_token=issue_token(user))


@auth_router.post("/token", response_model=TokenOut)
async def login_for_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """OAuth2-compatible token endpoint, used by the FastAPI /docs Authorize button."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    return TokenOut(access_token=issue_token(user))
