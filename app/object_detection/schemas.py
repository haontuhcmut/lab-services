from pydantic import BaseModel
from datetime import datetime


class UserHistoryModel(BaseModel):
    total_objects: int
    sample_name: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminReadData(UserHistoryModel):
    username: str
    email: str
