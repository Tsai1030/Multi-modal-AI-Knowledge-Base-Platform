from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from raganything import RAGAnything, RAGAnythingConfig

from app.rag.chroma_adapter import ChromaVectorDBStorage
from app.rag.embedding_adapter import BGEEmbeddingAdapter
from app.rag.llm_adapter import OllamaLLMAdapter, OllamaVisionAdapter

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


def _register_chroma_storage() -> None:
    """Inject ChromaVectorDBStorage into LightRAG's storage registry.

    LightRAG resolves vector_storage by string name via lightrag.kg.STORAGES.
    We patch the registry once at startup so LightRAG can locate our implementation.
    """
    from lightrag.kg import STORAGES
    STORAGES["ChromaVectorDBStorage"] = "app.rag.chroma_adapter"


class RAGEngine:
    """Manages the RAGAnything instance lifecycle as an application-level singleton.

    Initialised once in FastAPI lifespan (startup) and shut down on exit.
    All other components obtain the instance via RAGEngine.get_rag().
    """

    _rag_instance: RAGAnything | None = None
    _llm_adapter: OllamaLLMAdapter | None = None
    _vision_adapter: OllamaVisionAdapter | None = None
    _embedding_adapter: BGEEmbeddingAdapter | None = None

    @classmethod
    async def initialize(cls, settings: Settings) -> None:
        """Startup sequence:
        1. Register ChromaVectorDBStorage into LightRAG's STORAGES registry
        2. Build OllamaLLMAdapter (gpt-oss:latest) — text reasoning & dialogue
        3. Build OllamaVisionAdapter (llava:7b) — document image captioning
           OllamaVisionAdapter holds a reference to llm_adapter for plain-text fallback
        4. Build BGEEmbeddingAdapter (lazy-loaded BAAI/bge-m3)
        5. Build RAGAnythingConfig with ChromaDB as vector_storage
        6. Instantiate RAGAnything with injected llm/vision/embedding funcs
        """
        _register_chroma_storage()

        cls._llm_adapter = OllamaLLMAdapter(
            base_url=settings.ollama_base_url,
            model=settings.ollama_llm_model,
        )
        cls._vision_adapter = OllamaVisionAdapter(
            base_url=settings.ollama_base_url,
            model=settings.ollama_vision_model,
            llm_adapter=cls._llm_adapter,
        )
        cls._embedding_adapter = BGEEmbeddingAdapter(
            model_name=settings.embedding_model_name,
        )

        config = RAGAnythingConfig(
            working_dir=settings.rag_working_dir,
            parser="mineru",
            enable_image_processing=True,
            enable_table_processing=True,
            enable_equation_processing=True,
        )

        cls._rag_instance = RAGAnything(
            llm_model_func=cls._llm_adapter.as_llm_func(),
            vision_model_func=cls._vision_adapter.as_vision_func(),
            embedding_func=cls._embedding_adapter.to_embedding_func(),
            config=config,
            lightrag_kwargs={
                "vector_storage": "ChromaVectorDBStorage",
                "vector_db_storage_cls_kwargs": {
                    "cosine_better_than_threshold": 0.2,
                },
                "chroma_host": settings.chroma_host,
                "chroma_port": settings.chroma_port,
            },
        )

        logger.info("RAGEngine initialized successfully")

    @classmethod
    def get_rag(cls) -> RAGAnything:
        if cls._rag_instance is None:
            raise RuntimeError("RAGEngine has not been initialized. Call initialize() first.")
        return cls._rag_instance

    @classmethod
    def get_llm_adapter(cls) -> OllamaLLMAdapter:
        if cls._llm_adapter is None:
            raise RuntimeError("RAGEngine has not been initialized. Call initialize() first.")
        return cls._llm_adapter

    @classmethod
    async def shutdown(cls) -> None:
        cls._rag_instance = None
        cls._llm_adapter = None
        cls._vision_adapter = None
        cls._embedding_adapter = None
        logger.info("RAGEngine shut down")
