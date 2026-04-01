from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.message import Message
    from app.rag.llm_adapter import OllamaLLMAdapter


class ConversationCompactor:
    """Compresses long conversation history into a summary to prevent LLM context overflow.

    Triggered when message_count >= compact_threshold. Keeps the most recent
    compact_target messages intact and summarises the older portion via LLM.
    """

    COMPACT_PROMPT_TEMPLATE: str = (
        "以下是一段對話的歷史紀錄，請將其整理成一段簡潔的摘要，"
        "保留所有重要的問題、答案與關鍵資訊，以繁體中文回答：\n\n"
        "{conversation_history}\n\n"
        "請以「對話摘要：」開頭，輸出摘要內容。"
    )

    def __init__(
        self,
        llm_adapter: OllamaLLMAdapter,
        compact_threshold: int = 15,
        compact_target: int = 6,
    ) -> None:
        self._llm_adapter = llm_adapter
        self.compact_threshold = compact_threshold
        self.compact_target = compact_target

    def should_compact(self, message_count: int) -> bool:
        return message_count >= self.compact_threshold

    async def compact(
        self,
        messages: list[Message],
        keep_last_n: int,
    ) -> tuple[str, list[Message]]:
        """Compress old messages into a summary, keeping the most recent ones.

        Args:
            messages:    Full ordered message list for this session.
            keep_last_n: Number of recent messages to preserve unchanged.

        Returns:
            (summary_text, messages_to_keep)
        """
        if keep_last_n >= len(messages):
            # Nothing old enough to compress; summarise all and keep all.
            conversation_text = self._format_messages(messages)
            prompt = self.COMPACT_PROMPT_TEMPLATE.format(conversation_history=conversation_text)
            summary = await self._llm_adapter.complete(prompt)
            return summary, messages

        messages_to_keep = messages[-keep_last_n:]
        messages_to_compress = messages[:-keep_last_n]

        conversation_text = self._format_messages(messages_to_compress)
        prompt = self.COMPACT_PROMPT_TEMPLATE.format(conversation_history=conversation_text)
        summary = await self._llm_adapter.complete(prompt)
        return summary, messages_to_keep

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate: Chinese ~0.5 token/char, English ~0.25 token/char."""
        return len(text) // 3

    @staticmethod
    def _format_messages(messages: list[Message]) -> str:
        role_labels = {"user": "用戶", "assistant": "助理", "system": "系統"}
        lines = [
            f"{role_labels.get(msg.role.value, msg.role.value)}: {msg.content}"
            for msg in messages
        ]
        return "\n".join(lines)
