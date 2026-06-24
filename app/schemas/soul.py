from datetime import datetime

from pydantic import BaseModel


class SoulEntryOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    agent_id: str
    category: str
    key: str
    content: str
    version: int
    updated_at: datetime


class UpsertSoulRequest(BaseModel):
    content: str
    category: str = "learned"
