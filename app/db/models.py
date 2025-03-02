from datetime import datetime
from typing import List, Optional

from sqlalchemy.dialects.mysql import VARCHAR, TIMESTAMP, BOOLEAN
from sqlmodel import SQLModel, Field, Column, Relationship

import uuid


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    username: str = Field(nullable=False, unique=True)
    email: str = Field(nullable=False, unique=True)
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    role: str = Field(
        sa_column=Column(VARCHAR(255), nullable=False, server_default="user")
    )
    is_verified: bool = Field(sa_column=Column(BOOLEAN, default=False, nullable=False))
    hashed_password: str = Field(
        sa_column=Column(VARCHAR(255), nullable=False), exclude=True
    )
    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, default=datetime.now)
    )

    yolo_outputs: List["YoloOutput"] = Relationship(back_populates="user")


class YoloOutput(SQLModel, table=True):
    __tablename__ = "yolo_outputs"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    sample_name: str | None = Field(default=None)
    total_objects: int
    user_id: uuid.UUID = Field(foreign_key="users.uid", nullable=False)
    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, default=datetime.now)
    )

    user: Optional[User] = Relationship(back_populates="yolo_outputs")
