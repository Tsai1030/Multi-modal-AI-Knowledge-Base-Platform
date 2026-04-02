from __future__ import annotations

import numpy as np
import httpx

from lightrag.utils import EmbeddingFunc


class OllamaEmbeddingAdapter:
    """Embedding via Ollama /api/embed endpoint (runs on GPU via Ollama)."""

    EMBEDDING_DIM: int = 1024
    MAX_TOKEN_SIZE: int = 8192
    _BATCH_SIZE: int = 32

    def __init__(self, base_url: str, model: str = "bge-m3") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def embed(self, texts: list[str]) -> np.ndarray:
        all_vectors: list[np.ndarray] = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            for i in range(0, len(texts), self._BATCH_SIZE):
                batch = texts[i : i + self._BATCH_SIZE]
                response = await client.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._model, "input": batch},
                )
                response.raise_for_status()
                data = response.json()
                vectors = np.array(data["embeddings"], dtype=np.float32)
                all_vectors.append(vectors)

        if not all_vectors:
            return np.empty((0, self.EMBEDDING_DIM), dtype=np.float32)

        return np.vstack(all_vectors)

    def to_embedding_func(self) -> EmbeddingFunc:
        async def _embed_func(texts: list[str]) -> np.ndarray:
            return await self.embed(texts)

        return EmbeddingFunc(
            embedding_dim=self.EMBEDDING_DIM,
            max_token_size=self.MAX_TOKEN_SIZE,
            func=_embed_func,
            model_name=self._model,
        )
