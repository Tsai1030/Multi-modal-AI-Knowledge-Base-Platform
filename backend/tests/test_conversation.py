"""
Tests for multi-turn conversation management:
ConversationCompactor, ConversationService, ChatSessionService.

NOTE: All tests use mocks (no real DB or LLM calls).
TODO: After Docker Compose setup, add integration tests against real services and remove mocks.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.message import MessageRole


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_message(
    role: MessageRole = MessageRole.user,
    content: str = "test",
    is_compacted_summary: bool = False,
    msg_id: uuid.UUID | None = None,
) -> MagicMock:
    msg = MagicMock()
    msg.id = msg_id or uuid.uuid4()
    msg.role = role
    msg.content = content
    msg.is_compacted_summary = is_compacted_summary
    msg.token_count = len(content) // 3
    return msg


def _make_session(
    session_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    message_count: int = 0,
    compact_summary: str | None = None,
    is_compacted: bool = False,
    title: str = "新對話",
) -> MagicMock:
    session = MagicMock()
    session.id = session_id or uuid.uuid4()
    session.user_id = user_id or uuid.uuid4()
    session.message_count = message_count
    session.compact_summary = compact_summary
    session.is_compacted = is_compacted
    session.title = title
    return session


# ── ConversationCompactor ─────────────────────────────────────────────────────

class TestConversationCompactor:
    def _make_compactor(self, threshold: int = 15, target: int = 6):
        from app.rag.conversation_compactor import ConversationCompactor

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="對話摘要：這是摘要內容。")
        return ConversationCompactor(mock_llm, compact_threshold=threshold, compact_target=target), mock_llm

    def test_should_compact_below_threshold(self):
        compactor, _ = self._make_compactor(threshold=15)
        assert compactor.should_compact(14) is False

    def test_should_compact_at_threshold(self):
        compactor, _ = self._make_compactor(threshold=15)
        assert compactor.should_compact(15) is True

    def test_should_compact_above_threshold(self):
        compactor, _ = self._make_compactor(threshold=15)
        assert compactor.should_compact(20) is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_compact_calls_llm_and_splits_messages(self):
        """compact() summarises old messages and returns (summary, last-N msgs)."""
        compactor, mock_llm = self._make_compactor(threshold=15, target=6)
        messages = [_make_message(content=f"msg {i}") for i in range(10)]

        summary, kept = await compactor.compact(messages, keep_last_n=6)

        assert summary == "對話摘要：這是摘要內容。"
        assert len(kept) == 6
        assert kept == messages[-6:]
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_compact_keep_all_when_keep_n_exceeds_length(self):
        """When keep_last_n >= len(messages), all messages are kept."""
        compactor, _ = self._make_compactor()
        messages = [_make_message(content=f"msg {i}") for i in range(3)]

        _, kept = await compactor.compact(messages, keep_last_n=5)

        assert kept == messages

    def test_estimate_tokens_returns_length_divided_by_three(self):
        compactor, _ = self._make_compactor()
        assert compactor.estimate_tokens("a" * 90) == 30


# ── ConversationService ───────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
class TestConversationService:
    def _make_service(
        self,
        session: MagicMock | None = None,
        messages: list | None = None,
        compact_threshold: int = 15,
        compact_target: int = 6,
    ):
        from app.rag.conversation_compactor import ConversationCompactor
        from app.services.conversation_service import ConversationService

        session_repo = AsyncMock()
        message_repo = AsyncMock()

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="對話摘要：摘要文字。")
        compactor = ConversationCompactor(mock_llm, compact_threshold=compact_threshold, compact_target=compact_target)

        if session is not None:
            session_repo.get_by_id = AsyncMock(return_value=session)
        if messages is not None:
            message_repo.get_recent_by_session = AsyncMock(return_value=messages)

        svc = ConversationService(session_repo, message_repo, compactor)
        return svc, session_repo, message_repo

    async def test_get_context_assembles_system_history_and_current_question(self):
        """Normal flow: [system, ...history, current_question]."""
        msgs = [
            _make_message(MessageRole.user, "what is RAG?"),
            _make_message(MessageRole.assistant, "RAG is retrieval-augmented generation."),
        ]
        session = _make_session(message_count=2)
        svc, _, _ = self._make_service(session=session, messages=msgs)

        context = await svc.get_conversation_context(session.id, "tell me more")

        assert context[0]["role"] == "system"
        assert context[-1] == {"role": "user", "content": "tell me more"}
        middle_roles = [m["role"] for m in context[1:-1]]
        assert middle_roles == ["user", "assistant"]

    async def test_get_context_includes_compact_summary_as_assistant(self):
        """If session.compact_summary is set, it appears as assistant message."""
        session = _make_session(message_count=5, compact_summary="previous summary text")
        svc, _, _ = self._make_service(session=session, messages=[])

        context = await svc.get_conversation_context(session.id, "new question")

        summary_entries = [m for m in context if m["content"] == "previous summary text"]
        assert len(summary_entries) == 1
        assert summary_entries[0]["role"] == "assistant"

    async def test_get_context_filters_out_compacted_summary_db_markers(self):
        """is_compacted_summary=True DB messages are not duplicated into history body."""
        marker = _make_message(MessageRole.system, "old summary", is_compacted_summary=True)
        normal = _make_message(MessageRole.user, "hello")
        session = _make_session(message_count=2, compact_summary="old summary")
        svc, _, _ = self._make_service(session=session, messages=[marker, normal])

        context = await svc.get_conversation_context(session.id, "next")

        # compact_summary appears once (from session field), not twice (not from DB marker)
        assert [m["content"] for m in context].count("old summary") == 1

    async def test_get_context_triggers_compact_at_threshold(self):
        """message_count >= threshold causes compact to be executed."""
        msgs = [_make_message(MessageRole.user, f"msg {i}") for i in range(15)]
        session = _make_session(message_count=15)
        svc, session_repo, message_repo = self._make_service(
            session=session, messages=msgs, compact_threshold=15, compact_target=6
        )
        message_repo.get_recent_by_session = AsyncMock(side_effect=[msgs, msgs[-6:]])
        message_repo.create = AsyncMock(return_value=MagicMock())
        message_repo.delete = AsyncMock(return_value=True)
        session_repo.update_compact_data = AsyncMock()
        session_repo.increment_message_count = AsyncMock()

        context = await svc.get_conversation_context(session.id, "new question")

        session_repo.update_compact_data.assert_called_once()
        # After compact: [system, assistant(summary), ...6 msgs, user(new_question)]
        assert context[0]["role"] == "system"
        assert context[1]["role"] == "assistant"  # compact summary injected

    async def test_get_context_after_compact_is_length_bounded(self):
        """After compact, history entries ≤ compact_target plus system+summary+current."""
        msgs = [_make_message(MessageRole.user, f"msg {i}") for i in range(15)]
        session = _make_session(message_count=15)
        svc, session_repo, message_repo = self._make_service(
            session=session, messages=msgs, compact_threshold=15, compact_target=6
        )
        kept = msgs[-6:]
        message_repo.get_recent_by_session = AsyncMock(side_effect=[msgs, kept])
        message_repo.create = AsyncMock(return_value=MagicMock())
        message_repo.delete = AsyncMock(return_value=True)
        session_repo.update_compact_data = AsyncMock()
        session_repo.increment_message_count = AsyncMock()

        context = await svc.get_conversation_context(session.id, "q")

        # max = system(1) + summary(1) + compact_target(6) + current_q(1) = 9
        assert len(context) <= 9

    async def test_auto_title_updates_default_title(self):
        """auto_title_session truncates first 20 chars and sets as title."""
        session = _make_session(title="新對話 2024-01-01 12:00")
        svc, session_repo, _ = self._make_service(session=session, messages=[])
        session_repo.update_title = AsyncMock()

        long_msg = "What is machine learning and how does it work in practice?"
        await svc.auto_title_session(session.id, long_msg)

        session_repo.update_title.assert_called_once()
        new_title = session_repo.update_title.call_args[0][1]
        assert new_title == long_msg[:20]
        assert len(new_title) <= 20

    async def test_auto_title_skips_when_title_is_already_custom(self):
        """auto_title_session does nothing when title does not start with '新對話'."""
        session = _make_session(title="My Custom Title")
        svc, session_repo, _ = self._make_service(session=session, messages=[])
        session_repo.update_title = AsyncMock()

        await svc.auto_title_session(session.id, "some question")

        session_repo.update_title.assert_not_called()

    async def test_save_user_message_increments_message_count(self):
        """save_user_message creates message and increments session counter."""
        session_id = uuid.uuid4()
        svc, session_repo, message_repo = self._make_service()
        message_repo.create = AsyncMock(return_value=MagicMock())
        session_repo.increment_message_count = AsyncMock()

        await svc.save_user_message(session_id, "hello", "hybrid")

        message_repo.create.assert_called_once()
        session_repo.increment_message_count.assert_called_once_with(session_id)

    async def test_save_assistant_message_updates_last_message_at(self):
        """save_assistant_message updates session's last_message_at timestamp."""
        session_id = uuid.uuid4()
        svc, session_repo, message_repo = self._make_service()
        message_repo.create = AsyncMock(return_value=MagicMock())
        session_repo.update_last_message = AsyncMock()
        session_repo.increment_message_count = AsyncMock()

        await svc.save_assistant_message(session_id, "answer", rag_sources=["doc1"])

        session_repo.update_last_message.assert_called_once()
        session_repo.increment_message_count.assert_called_once_with(session_id)


# ── ChatSessionService ────────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
class TestChatSessionService:
    def _make_service(self, session: MagicMock | None = None):
        from app.services.chat_session_service import ChatSessionService

        session_repo = AsyncMock()
        message_repo = AsyncMock()
        if session is not None:
            session_repo.get_by_id = AsyncMock(return_value=session)
        return ChatSessionService(session_repo, message_repo), session_repo, message_repo

    async def test_create_session_uses_default_title_starting_with_new_conversation(self):
        """create_session produces title starting with '新對話'."""
        svc, session_repo, _ = self._make_service()
        session_repo.create = AsyncMock(return_value=MagicMock())

        await svc.create_session(user_id=uuid.uuid4())

        call_data = session_repo.create.call_args[0][0]
        assert call_data["title"].startswith("新對話")
        assert call_data["query_mode"] == "hybrid"

    async def test_create_session_accepts_custom_query_mode(self):
        """create_session passes the given query_mode through."""
        svc, session_repo, _ = self._make_service()
        session_repo.create = AsyncMock(return_value=MagicMock())

        await svc.create_session(user_id=uuid.uuid4(), query_mode="local")

        call_data = session_repo.create.call_args[0][0]
        assert call_data["query_mode"] == "local"

    async def test_list_sessions_passes_pagination_to_repo(self):
        """list_sessions forwards skip and limit to the repository."""
        uid = uuid.uuid4()
        svc, session_repo, _ = self._make_service()
        session_repo.get_by_user = AsyncMock(return_value=[])

        await svc.list_sessions(uid, skip=5, limit=10)

        session_repo.get_by_user.assert_called_once_with(uid, skip=5, limit=10)

    async def test_get_session_with_messages_raises_authorization_for_wrong_user(self):
        """get_session_with_messages raises AuthorizationError for non-owner."""
        from app.core.exceptions import AuthorizationError

        session = _make_session(user_id=uuid.uuid4())
        svc, _, message_repo = self._make_service(session=session)
        message_repo.get_by_session = AsyncMock(return_value=[])

        with pytest.raises(AuthorizationError):
            await svc.get_session_with_messages(session.id, uuid.uuid4())

    async def test_get_session_with_messages_returns_session_and_messages(self):
        """get_session_with_messages returns (session, messages) for the owner."""
        uid = uuid.uuid4()
        session = _make_session(user_id=uid)
        msgs = [_make_message()]
        svc, _, message_repo = self._make_service(session=session)
        message_repo.get_by_session = AsyncMock(return_value=msgs)

        result_session, result_msgs = await svc.get_session_with_messages(session.id, uid)

        assert result_session is session
        assert result_msgs is msgs

    async def test_rename_session_raises_authorization_for_wrong_user(self):
        """rename_session raises AuthorizationError if caller is not the owner."""
        from app.core.exceptions import AuthorizationError

        session = _make_session(user_id=uuid.uuid4())
        svc, _, _ = self._make_service(session=session)

        with pytest.raises(AuthorizationError):
            await svc.rename_session(session.id, uuid.uuid4(), "New Title")

    async def test_delete_session_raises_not_found_for_unknown_session(self):
        """delete_session raises NotFoundError when session does not exist."""
        from app.core.exceptions import NotFoundError

        svc, session_repo, _ = self._make_service()
        session_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await svc.delete_session(uuid.uuid4(), uuid.uuid4())

    async def test_delete_session_raises_authorization_for_wrong_user(self):
        """delete_session raises AuthorizationError when caller is not the owner."""
        from app.core.exceptions import AuthorizationError

        session = _make_session(user_id=uuid.uuid4())
        svc, _, _ = self._make_service(session=session)

        with pytest.raises(AuthorizationError):
            await svc.delete_session(session.id, uuid.uuid4())
