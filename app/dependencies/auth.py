"""FastAPI dependency that resolves the current authenticated user from a JWT."""
from __future__ import annotations

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotAuthenticatedError
from app.core.security import TokenType, decode_token
from app.models.models import User
from app.repositories.user_repository import UserRepository

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise NotAuthenticatedError("Missing bearer token.")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise NotAuthenticatedError("Token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise NotAuthenticatedError("Invalid token.") from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise NotAuthenticatedError("Invalid token type; expected access token.")

    user_id = payload.get("sub")
    if not user_id:
        raise NotAuthenticatedError("Token missing subject.")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise NotAuthenticatedError("User not found or inactive.")

    return user
