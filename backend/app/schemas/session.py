from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionCreateRequest(BaseModel):
    query_mode: str = "hybrid"


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    query_mode: str
    message_count: int
    last_message_at: datetime | None
    is_compacted: bool
    created_at: datetime


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int


class SessionRenameRequest(BaseModel):
    title: str
