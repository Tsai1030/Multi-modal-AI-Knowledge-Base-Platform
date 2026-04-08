from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Callable
from typing import Any

import httpx


class OllamaLLMAdapter:
    """Wraps Ollama /api/chat to provide llm_model_func callable for LightRAG/RAGAnything.

    LightRAG calls the returned func as:
        await llm_func(prompt, system_prompt=None, history_messages=[], stream=False, **kwargs)
    The model is pre-bound via as_llm_func(); LightRAG never passes model as an argument.
    """

    def __init__(self, base_url: str, model: str, timeout: int = 300) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list[dict[str, str]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str:
        messages = self._build_messages(prompt, system_prompt, history_messages or [])
        payload = {"model": self._model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def complete_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(prompt, system_prompt, history_messages or [])
        payload = {"model": self._model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break

    def as_llm_func(self) -> Callable:
        """Return callable matching LightRAG llm_model_func signature (model pre-bound)."""

        async def llm_func(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict[str, str]] | None = None,
            stream: bool = False,
            **kwargs: Any,
        ) -> Any:
            if stream:
                return self.complete_stream(
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    **kwargs,
                )

            return await self.complete(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                stream=stream,
                **kwargs,
            )

        return llm_func

    @staticmethod
    def _build_messages(
        prompt: str,
        system_prompt: str | None,
        history_messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})
        return messages


class OllamaVisionAdapter:
    """Wraps Ollama multimodal endpoint for document image captioning (gemma4:e2b).

    Used exclusively by RAGAnything during document ingestion to caption embedded images.
    Real-time chat always uses OllamaLLMAdapter (gemma4:e2b).

    RAGAnything calls vision_model_func in two patterns:
        - Pure text:   await vision_func(content, system_prompt=system_prompt)
        - Multimodal:  await vision_func("", messages=messages)
    """

    def __init__(
        self,
        base_url: str,
        model: str = "gemma4:e2b",
        timeout: int = 120,
        llm_adapter: OllamaLLMAdapter | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._llm_adapter = llm_adapter

    async def vision_complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list[dict] | None = None,
        image_data: str | None = None,
        messages: list | None = None,
        **kwargs: Any,
    ) -> str:
        """Handle vision requests from RAGAnything.

        Priority order:
        1. messages provided  → VLM Enhanced Query: forward full messages to gemma4
        2. image_data provided → single image analysis with base64 payload
        3. fallback            → pure text; delegate to llm_adapter if available
        """
        if messages:
            return await self._chat_with_messages(messages)
        if image_data:
            return await self._chat_with_image(prompt, image_data, system_prompt)
        if self._llm_adapter:
            return await self._llm_adapter.complete(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
            )
        return await self._chat_text_only(prompt, system_prompt)

    def as_vision_func(self) -> Callable:
        """Return callable matching RAGAnything vision_model_func signature."""

        async def vision_func(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict] | None = None,
            image_data: str | None = None,
            messages: list | None = None,
            **kwargs: Any,
        ) -> str:
            return await self.vision_complete(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                image_data=image_data,
                messages=messages,
                **kwargs,
            )

        return vision_func

    async def _chat_with_messages(self, messages: list) -> str:
        payload = {
            "model": self._model,
            "messages": self._normalize_multimodal_messages_for_ollama(messages),
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            if resp.status_code == 404 and self._model != "gemma4:e2b":
                payload["model"] = "gemma4:e2b"
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _chat_with_image(
        self, prompt: str, image_data: str, system_prompt: str | None
    ) -> str:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": prompt or "Please describe this image in detail.",
            "images": [image_data],
        })
        payload = {"model": self._model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            if resp.status_code == 404 and self._model != "gemma4:e2b":
                payload["model"] = "gemma4:e2b"
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _chat_text_only(self, prompt: str, system_prompt: str | None) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self._model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    @staticmethod
    def _normalize_multimodal_messages_for_ollama(messages: list) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                normalized.append({"role": role, "content": content})
                continue

            if not isinstance(content, list):
                normalized.append({"role": role, "content": str(content)})
                continue

            text_parts: list[str] = []
            images: list[str] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_type = part.get("type")
                if part_type == "text":
                    text_parts.append(str(part.get("text", "")))
                elif part_type == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if isinstance(url, str) and "base64," in url:
                        images.append(url.split("base64,", 1)[1])

            normalized_msg: dict[str, Any] = {
                "role": role,
                "content": "\n".join([t for t in text_parts if t]).strip()
                or "Please analyze this image.",
            }
            if images:
                normalized_msg["images"] = images
            normalized.append(normalized_msg)

        return normalized
