from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.auth.services import UserService
from app.auth.schemas import (
    UserCreateModel,
    UserLoginModel,
    PasswordResetRequestModel,
    PasswordResetConfirmModel,
)
from app.auth.utils import (
    create_url_safe_token,
    decode_url_safe_token,
    verify_password,
    create_access_token,
    generate_hashed_password,
)
from app.auth.dependencies import (
    RefreshTokenBearer,
    AccessTokenBearer,
    get_current_user,
    RoleChecker,
)
from app.db.redis import add_jti_to_blocklist
from sqlmodel.ext.asyncio.session import AsyncSession
from app.celery_tasks import send_email
from app.config import Config
from app.db.session import get_session

auth_router = APIRouter()
user_service = UserService()
access_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(["admin", "user"]))
role_checker_admin = Depends(RoleChecker(["admin"]))


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user_account(
    user_data: UserCreateModel,
    session: AsyncSession = Depends(get_session),
):
    email = user_data.email
    user_exists = await user_service.user_exists(email, session)
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Email already exists",
                "error_code": "user_exists",
            },
        )
    username = user_data.username
    username_exists = await user_service.username_exists(username, session)
    if username_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "messenge": "The chosen username is already in use. Please select a difference one.",
                "error_code": "usrename_exists",
            },
        )
    new_user = await user_service.create_user(user_data, session)
    token = create_url_safe_token({"email": email})
    link = f"http://{Config.DOMAIN}/api/v1/auth/verify/{token}"
    html = f"""
    <h1>Verify your Email</h1>
    <p>Please click this <a href="{link}"link</a> to verify your email</p>
"""
    emails = [email]
    subject = "Verify your email"
    send_email.delay(emails, subject, html)

    return {
        "message": "Account created! Check email to verify your account",
        "user": new_user,
    }


@auth_router.get("/verify/{token}")
async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):
    token_data = decode_url_safe_token(token)
    user_email = token_data.get("email")
    if user_email:
        user = await user_service.get_user_by_email(user_email, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "error_code": "user_not_found",
                },
            )
        await user_service.update_user(user, {"is_verified": True}, session)
        return JSONResponse(
            content={"message": "Account verified successfully!"},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={"message": "Error occurred during verification"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@auth_router.post("/login")
async def login_users(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    email = login_data.email
    password = login_data.password
    user = await user_service.get_user_by_email(email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user is not None:
        password_valid = verify_password(password, user.hashed_password)
        if password_valid:
            access_token_expires = timedelta(
                minutes=Config.ACCESS_TOKEN_EXPIRES_MINUTES
            )
            access_token = create_access_token(
                user_data=dict(
                    email=user.email,
                    user_id=str(user.uid),
                    role=user.role,
                ),
                expire_timedelta=access_token_expires,
            )
            refresh_token_expires = timedelta(
                days=Config.REFRESH_TOKEN_EXPIRES_DAYS_DEFAULT
            )
            refresh_token = create_access_token(
                user_data=dict(email=user.email, user_id=str(user.uid)),
                expire_timedelta=refresh_token_expires,
                refresh=True,
            )
            return JSONResponse(
                content={
                    "message": "Login successfully!",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {"email": user.email, "uid": str(user.uid)},
                }
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@auth_router.get("/refresh_token")
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    expires_timestamp = token_details["exp"]
    if datetime.fromtimestamp(expires_timestamp, timezone.utc) > datetime.now(
        timezone.utc
    ):
        new_access_token = create_access_token(user_data=token_details["user"])
        return JSONResponse(content={"access_token": new_access_token})
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "message": "Token is invalid or expired",
            "resolution": "Please get new token",
            "error_code": "invalid_token",
        },
    )


@auth_router.get("/me")
async def get_current_user(user=Depends(get_current_user)):
    return user


@auth_router.get("/logout")
async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):
    jti = token_details["jti"]
    await add_jti_to_blocklist(jti)
    return JSONResponse(
        content={"message": "Logged out successfully!"}, status_code=status.HTTP_200_OK
    )


@auth_router.post("/password-reset-request")
async def password_reset_request(email_data: PasswordResetRequestModel):
    email = email_data.email
    token = create_url_safe_token({"email": email})
    link = f"http://{Config.DOMAIN}/api/v1/auth/password-reset-confirm/{token}"
    html = f"""
    <h1>Reset your password</h1>
    <p>Please click this <a href="{link}"> link</a> to your reset password</p>
"""
    subject = "Reset your password"

    send_email.delay(email, subject, html)

    return JSONResponse(
        content={
            "message": "Please check your email for instruction to reset your password",
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/password-reset-confirm/{token}")
async def reset_account_password(
    token: str,
    passwords: PasswordResetConfirmModel,
    session: AsyncSession = Depends(get_session),
):
    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password

    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password do not match"
        )
    token_data = decode_url_safe_token(token)
    user_email = token_data.get("email")
    if user_email:
        user = await user_service.get_user_by_email(user_email, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bear"},
            )
        hashed_password = generate_hashed_password(new_password)
        await user_service.update_user(
            user, {"hashed_password": hashed_password}, session
        )

        return JSONResponse(
            content={"message": "Password reset successfully!"},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={"Error occurred during password reset."},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
