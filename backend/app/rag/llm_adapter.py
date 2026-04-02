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
    """Wraps Ollama multimodal endpoint for document image captioning (llava:7b).

    Used exclusively by RAGAnything during document ingestion to caption embedded images.
    Real-time chat always uses OllamaLLMAdapter (gpt-oss:latest).

    RAGAnything calls vision_model_func in two patterns:
        - Pure text:   await vision_func(content, system_prompt=system_prompt)
        - Multimodal:  await vision_func("", messages=messages)
    """

    def __init__(
        self,
        base_url: str,
        model: str = "llava:7b",
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
        1. messages provided  → VLM Enhanced Query: forward full messages to llava
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
        payload = {"model": self._model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _chat_with_image(
        self, prompt: str, image_data: str, system_prompt: str | None
    ) -> str:
        content: list[dict] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
        ]
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        payload = {"model": self._model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
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
