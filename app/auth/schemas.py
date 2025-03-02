from pydantic import BaseModel, Field
from app.config import Config


class UserCreateModel(BaseModel):
    first_name: str = Field(max_length=25)
    last_name: str = Field(max_length=25)
    username: str = Field(max_length=32)
    email: str = Field(max_length=125)
    password: str = Field(min_length=6)

    model_config = dict(
        json_schema_extra=dict(
            example=dict(
                first_name="John",
                last_name="Doe",
                username="johndoe",
                email="johndoe@example.com",
                password="testpass123",
            )
        )
    )


class EmailModel(BaseModel):
    addresses: list[str]


class UserLoginModel(BaseModel):
    email: str
    password: str


class PasswordResetRequestModel(BaseModel):
    email: list[str]


class PasswordResetConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str


class AdminCreateModel(BaseModel):
    first_name: str = Config.FIRST_NAME
    last_name: str = Config.LAST_NAME
    username: str = Config.ADMIN_NAME
    email: str = Config.EMAIL
    password: str = Config.PASSWORD
