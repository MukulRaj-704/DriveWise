from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.schemas import TokenPair, UserLogin, UserRegister


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, payload: UserRegister) -> User:
        existing = await self.repo.get_by_email(payload.email)
        if existing:
            raise UserAlreadyExistsError()

        return await self.repo.create(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )

    async def login(self, payload: UserLogin) -> TokenPair:
        user = await self.repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError()

        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )
