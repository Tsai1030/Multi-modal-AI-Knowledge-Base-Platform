from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING

from lightrag.utils import EmbeddingFunc

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class BGEEmbeddingAdapter:
    """Local BAAI/bge-m3 embedding via sentence-transformers.

    Lazy-loads the model on first call (thread-safe). Runs CPU-bound encode()
    in an asyncio executor to avoid blocking the event loop.
    """

    EMBEDDING_DIM: int = 1024
    MAX_TOKEN_SIZE: int = 8192
    _BATCH_SIZE: int = 32

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu") -> None:
        self._model_name = model_name
        self._device = device
        self._model: SentenceTransformer | None = None
        self._lock = threading.Lock()

    def _ensure_model_loaded(self) -> None:
        """Thread-safe lazy load of SentenceTransformer model."""
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name, device=self._device)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Runs model.encode() in a thread-pool executor."""
        self._ensure_model_loaded()

        def _encode() -> list[list[float]]:
            all_vectors: list[list[float]] = []
            for i in range(0, len(texts), self._BATCH_SIZE):
                batch = texts[i : i + self._BATCH_SIZE]
                vectors = self._model.encode(batch, convert_to_numpy=True)
                all_vectors.extend(v.tolist() for v in vectors)
            return all_vectors

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _encode)

    def to_embedding_func(self) -> EmbeddingFunc:
        """Return a LightRAG EmbeddingFunc wrapping this adapter."""

        async def _embed_func(texts: list[str]) -> list[list[float]]:
            return await self.embed(texts)

        return EmbeddingFunc(
            embedding_dim=self.EMBEDDING_DIM,
            max_token_size=self.MAX_TOKEN_SIZE,
            func=_embed_func,
            model_name=self._model_name,
        )
