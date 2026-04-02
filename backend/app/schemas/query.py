from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    session_id: UUID
    question: str = Field(min_length=1, max_length=2000)
    mode: str = "hybrid"


class SSEEvent(BaseModel):
    type: str  # "token" | "done" | "error" | "sources"
    content: str | None = None
    sources: list[str] | None = None
    session_id: str | None = None
    message_id: str | None = None
