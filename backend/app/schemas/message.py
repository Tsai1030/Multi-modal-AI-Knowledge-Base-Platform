from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.session import SessionResponse


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: str
    content: str
    is_compacted_summary: bool
    rag_sources: list[str] | None
    query_mode: str | None
    created_at: datetime

    @classmethod
    def from_orm_message(cls, msg) -> "MessageResponse":
        import json
        sources = None
        if msg.rag_sources:
            try:
                sources = json.loads(msg.rag_sources)
            except (ValueError, TypeError):
                sources = None
        return cls(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role.value if hasattr(msg.role, "value") else msg.role,
            content=msg.content,
            is_compacted_summary=msg.is_compacted_summary,
            rag_sources=sources,
            query_mode=msg.query_mode,
            created_at=msg.created_at,
        )


class SessionDetailResponse(BaseModel):
    session: SessionResponse
    messages: list[MessageResponse]
