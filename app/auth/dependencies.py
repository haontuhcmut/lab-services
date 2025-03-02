from typing import Any, List

from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi import Request, Depends
from app.auth.utils import decode_token
from fastapi import HTTPException, status
from app.db.redis import token_in_blocklist
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.auth.services import UserService
from app.db.models import User

user_service = UserService()


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        creds = await super().__call__(request)
        token = creds.credentials
        token_data = decode_token(token)
        if not self.token_valid(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Token is invalid Or expired",
                    "resolution": "Please get new token",
                    "error_code": "invalid_token",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        if await token_in_blocklist(token_data["jti"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Token is invalid Or expired",
                    "resolution": "Please get new token",
                    "error_code": "invalid_token",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        self.verify_token_data(token_data)

        return token_data

    def token_valid(self, token: str) -> bool:
        token_data = decode_token(token)
        return token_data is not None

    def verify_token_data(self, token_data):
        raise NotImplementedError("Please Override this method in child classes")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data["refresh"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Please provide a valid access token",
                    "resolution": "Please get an access token",
                    "error_code": "access_token_required",
                },
            )


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data) -> None:
        if token_data and not token_data["refresh"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Please provide a valid refresh token",
                    "resolution": "Please get an refresh token",
                    "error_code": "refresh_token_required",
                },
            )


async def get_current_user(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_email = token_details["user"]["email"]
    user = await user_service.get_user_by_email(user_email, session)
    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> Any:
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Account Not verified",
                    "error_code": "account_not_verified",
                    "resolution": "Please check your email for verification details",
                },
            )

        if current_user.role in self.allowed_roles:
            return True
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "You do not have enough permissions to perform this action",
                "error_code": "insufficient_permissions",
            },
        )
