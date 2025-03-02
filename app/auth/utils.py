import logging
import uuid

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from datetime import timedelta, timezone, datetime
from app.config import Config
from fastapi import HTTPException, status
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


pwd_context = CryptContext(
    schemes=["bcrypt"],
    # deprecated="auto"
)


def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token, key=Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM]
        )
        return token_data
    except jwt.PyJWTError as e:
        logging.exception(e)
        return None


def generate_hashed_password(password: str) -> str:
    hashed_password = pwd_context.hash(password)
    return hashed_password


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict, expire_timedelta: timedelta | None = None, refresh: bool = False
):
    payload = {}

    payload["user"] = user_data

    if expire_timedelta:
        expires = datetime.now(timezone.utc) + expire_timedelta
    else:
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=Config.ACCESS_TOKEN_EXPIRES_DEFAULT
        )
    payload["exp"] = expires
    payload["jti"] = str(uuid.uuid4())
    payload["refresh"] = refresh

    access_token = jwt.encode(
        payload, key=Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM
    )

    return access_token


def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            token, key=Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM]
        )

        return token_data

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )


serializer = URLSafeTimedSerializer(
    secret_key=Config.JWT_SECRET, salt="email-configuration"
)


def create_url_safe_token(data: dict):
    token = serializer.dumps(data)
    return token


def decode_url_safe_token(token: str):
    try:
        token_data = serializer.loads(token, max_age=3600)
        return token_data
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid token.",
        )
