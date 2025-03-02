import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.testing.suite.test_reflection import users
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.models import User
from app.auth.schemas import UserCreateModel, AdminCreateModel
from app.auth.utils import generate_hashed_password


class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        results = await session.exec(statement)
        user = results.first()
        return user

    async def user_exists(self, email: str, session: AsyncSession):
        user = await self.get_user_by_email(email, session)
        return True if user is not None else False

    async def get_user_by_username(self, username: str, session: AsyncSession):
        statement = select(User).where(User.username == username)
        results = await session.exec(statement)
        user = results.first()
        return user

    async def username_exists(self, username: str, session: AsyncSession):
        user = await self.get_user_by_username(username, session)
        return True if user is not None else False

    async def create_user(self, user_data: UserCreateModel, session: AsyncSession):
        hashed_password = generate_hashed_password(user_data.password)
        user_data_dict = user_data.model_dump(exclude={"password"})
        new_user = User(**user_data_dict, hashed_password=hashed_password)
        new_user.role = "user"

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        for k, v in user_data.items():
            setattr(user, k, v)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


class AdminService(UserService):
    async def create_admin(self, admin_data: AdminCreateModel, session: AsyncSession):
        email = admin_data.email
        admin_exists = await self.user_exists(email, session)
        if admin_exists:
            return "Email already exists"
        admin_name = admin_data.username
        admin_name_exists = await self.username_exists(admin_name, session)
        if admin_name_exists:
            return "Admin name already exists"
        hashed_password = generate_hashed_password(admin_data.password)
        user_data_dict = admin_data.model_dump(exclude={"password"})
        new_admin = User(**user_data_dict, hashed_password=hashed_password)
        new_admin.role = "admin"
        new_admin.is_verified = True
        session.add(new_admin)
        await session.commit()
