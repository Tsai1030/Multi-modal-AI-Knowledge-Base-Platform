import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(UUIDMixin, TimestampMixin, Base):
    """A single message within a chat session."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, native_enum=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_compacted_summary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    rag_sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
