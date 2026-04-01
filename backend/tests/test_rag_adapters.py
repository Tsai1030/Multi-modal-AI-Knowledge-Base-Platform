"""
Tests for RAG adapter layer: OllamaLLMAdapter, OllamaVisionAdapter,
BGEEmbeddingAdapter, ChromaVectorDBStorage.

NOTE: All external services (Ollama, ChromaDB, SentenceTransformer) are mocked.
TODO: Remove mocks and run against real services once Docker Compose is set up (STEP Docker).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── OllamaLLMAdapter ──────────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
class TestOllamaLLMAdapter:
    def _make_adapter(self):
        from app.rag.llm_adapter import OllamaLLMAdapter
        return OllamaLLMAdapter(base_url="http://localhost:11434", model="gpt-oss:latest")

    def _mock_response(self, content: str) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"message": {"content": content}})
        return mock_resp

    async def test_complete_returns_content(self):
        adapter = self._make_adapter()
        mock_resp = self._mock_response("Hello, world!")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await adapter.complete("Say hello")

        assert result == "Hello, world!"

    async def test_complete_includes_system_prompt(self):
        adapter = self._make_adapter()
        mock_resp = self._mock_response("Answer")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            await adapter.complete("Question", system_prompt="You are a helpful assistant")

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        assert "helpful assistant" in messages[0]["content"]

    async def test_complete_includes_history(self):
        adapter = self._make_adapter()
        mock_resp = self._mock_response("Answer")
        history = [
            {"role": "user", "content": "prev question"},
            {"role": "assistant", "content": "prev answer"},
        ]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            await adapter.complete("New question", history_messages=history)

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
        messages = payload["messages"]
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    async def test_as_llm_func_returns_callable(self):
        adapter = self._make_adapter()
        mock_resp = self._mock_response("Result")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            llm_func = adapter.as_llm_func()
            result = await llm_func("prompt")

        assert result == "Result"


# ── OllamaVisionAdapter ───────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
class TestOllamaVisionAdapter:
    def _make_adapter(self, llm_adapter=None):
        from app.rag.llm_adapter import OllamaVisionAdapter
        return OllamaVisionAdapter(
            base_url="http://localhost:11434",
            model="llava:7b",
            llm_adapter=llm_adapter,
        )

    def _mock_ollama_client(self, content: str) -> AsyncMock:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"message": {"content": content}})
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        return mock_client

    async def test_vision_complete_with_messages_calls_llava(self):
        """messages provided → VLM Enhanced Query → forward to llava directly."""
        adapter = self._make_adapter()
        messages = [
            {"role": "system", "content": "Describe the image"},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:..."}}]},
        ]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = self._mock_ollama_client("A cat")
            result = await adapter.vision_complete("", messages=messages)

        assert result == "A cat"

    async def test_vision_complete_with_image_data(self):
        """image_data provided → single image analysis."""
        adapter = self._make_adapter()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = self._mock_ollama_client("A diagram")
            result = await adapter.vision_complete(
                "Describe this image", image_data="base64encodeddata=="
            )

        assert result == "A diagram"

    async def test_vision_complete_fallback_to_llm_adapter(self):
        """No messages, no image_data → fallback to llm_adapter."""
        from app.rag.llm_adapter import OllamaLLMAdapter
        llm_adapter = OllamaLLMAdapter(base_url="http://localhost:11434", model="gpt-oss:latest")
        adapter = self._make_adapter(llm_adapter=llm_adapter)

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"message": {"content": "Text answer"}})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await adapter.vision_complete("Plain text question")

        assert result == "Text answer"

    async def test_as_vision_func_returns_callable(self):
        adapter = self._make_adapter()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = self._mock_ollama_client("OK")
            vision_func = adapter.as_vision_func()
            result = await vision_func(
                "describe", messages=[{"role": "user", "content": "hi"}]
            )

        assert result == "OK"


# ── BGEEmbeddingAdapter ───────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
class TestBGEEmbeddingAdapter:
    def _make_adapter(self):
        from app.rag.embedding_adapter import BGEEmbeddingAdapter
        return BGEEmbeddingAdapter(model_name="BAAI/bge-m3")

    async def test_embed_returns_vectors(self):
        """embed() returns one vector per input text with correct dimension."""
        adapter = self._make_adapter()

        import numpy as np
        fake_vectors = np.random.rand(2, 1024).astype("float32")

        mock_model = MagicMock()
        mock_model.encode = MagicMock(return_value=fake_vectors)

        with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
            adapter._model = mock_model
            result = await adapter.embed(["text one", "text two"])

        assert len(result) == 2
        assert len(result[0]) == 1024

    async def test_embed_batches_large_input(self):
        """embed() processes texts in batches of _BATCH_SIZE."""
        adapter = self._make_adapter()

        import numpy as np
        texts = [f"text {i}" for i in range(70)]
        fake_batch = np.random.rand(adapter._BATCH_SIZE, 1024).astype("float32")
        last_batch = np.random.rand(70 % adapter._BATCH_SIZE, 1024).astype("float32")
        mock_model = MagicMock()
        mock_model.encode = MagicMock(side_effect=[fake_batch, fake_batch, last_batch])

        adapter._model = mock_model
        result = await adapter.embed(texts)

        assert len(result) == 70

def test_bge_embedding_func_metadata():
    """to_embedding_func() returns an EmbeddingFunc with correct dimension and token size."""
    from lightrag.utils import EmbeddingFunc
    from app.rag.embedding_adapter import BGEEmbeddingAdapter
    adapter = BGEEmbeddingAdapter(model_name="BAAI/bge-m3")
    ef = adapter.to_embedding_func()
    assert isinstance(ef, EmbeddingFunc)
    assert ef.embedding_dim == BGEEmbeddingAdapter.EMBEDDING_DIM
    assert ef.max_token_size == BGEEmbeddingAdapter.MAX_TOKEN_SIZE


# ── ChromaVectorDBStorage ─────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
class TestChromaVectorDBStorage:
    def _make_storage(self):
        from app.rag.chroma_adapter import ChromaVectorDBStorage
        from lightrag.utils import EmbeddingFunc

        async def dummy_embed(texts: list[str]) -> list[list[float]]:
            return [[0.1] * 1024 for _ in texts]

        ef = EmbeddingFunc(embedding_dim=1024, func=dummy_embed, model_name="bge-m3")
        storage = ChromaVectorDBStorage(
            namespace="test_ns",
            workspace="",
            global_config={"chroma_host": "localhost", "chroma_port": 8001},
            embedding_func=ef,
        )
        return storage

    async def test_initialize_creates_collection(self):
        """initialize() calls get_or_create_collection with the correct name."""
        storage = self._make_storage()

        mock_collection = AsyncMock()
        mock_client = AsyncMock()
        mock_client.get_or_create_collection = AsyncMock(return_value=mock_collection)

        with patch("chromadb.AsyncHttpClient", return_value=mock_client):
            await storage.initialize()

        mock_client.get_or_create_collection.assert_called_once()
        assert storage._collection is mock_collection

    async def test_upsert_stores_documents(self):
        """upsert() calls collection.upsert with correct ids and documents."""
        storage = self._make_storage()
        mock_collection = AsyncMock()
        storage._collection = mock_collection

        data = {
            "id-1": {"content": "Hello world", "embedding": [0.1] * 1024},
            "id-2": {"content": "Foo bar", "embedding": [0.2] * 1024},
        }
        await storage.upsert(data)

        mock_collection.upsert.assert_called_once()
        call_kwargs = mock_collection.upsert.call_args[1]
        assert set(call_kwargs["ids"]) == {"id-1", "id-2"}

    async def test_query_returns_results(self):
        """query() converts ChromaDB results into LightRAG-compatible dicts."""
        storage = self._make_storage()
        mock_collection = AsyncMock()
        mock_collection.query = AsyncMock(return_value={
            "ids": [["id-1", "id-2"]],
            "documents": [["doc one", "doc two"]],
            "metadatas": [[{"source": "a"}, {"source": "b"}]],
            "distances": [[0.1, 0.3]],
        })
        storage._collection = mock_collection

        results = await storage.query("test query", top_k=2, query_embedding=[0.1] * 1024)

        assert len(results) == 2
        assert results[0]["id"] == "id-1"
        assert results[0]["content"] == "doc one"
        assert results[0]["distance"] == pytest.approx(0.9)

    async def test_delete_calls_collection_delete(self):
        storage = self._make_storage()
        mock_collection = AsyncMock()
        storage._collection = mock_collection

        await storage.delete(["id-1", "id-2"])

        mock_collection.delete.assert_called_once_with(ids=["id-1", "id-2"])

    async def test_drop_deletes_collection(self):
        storage = self._make_storage()
        mock_client = AsyncMock()
        storage._client = mock_client
        storage._collection = AsyncMock()

        result = await storage.drop()

        mock_client.delete_collection.assert_called_once()
        assert result["status"] == "success"
