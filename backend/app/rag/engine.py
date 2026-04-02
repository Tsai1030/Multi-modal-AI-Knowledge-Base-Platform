from __future__ import annotations

import logging
import os
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
    from lightrag.kg import STORAGES, STORAGE_ENV_REQUIREMENTS, STORAGE_IMPLEMENTATIONS

    STORAGES["ChromaVectorDBStorage"] = "app.rag.chroma_adapter"

    vector_implementations = STORAGE_IMPLEMENTATIONS["VECTOR_STORAGE"]["implementations"]
    if "ChromaVectorDBStorage" not in vector_implementations:
        vector_implementations.append("ChromaVectorDBStorage")

    STORAGE_ENV_REQUIREMENTS.setdefault("ChromaVectorDBStorage", [])


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
        cls._ensure_libreoffice_in_path()

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
        import torch
        embedding_device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Embedding device: %s", embedding_device)
        cls._embedding_adapter = BGEEmbeddingAdapter(
            model_name=settings.embedding_model_name,
            device=embedding_device,
        )

        logger.info("Pre-warming embedding model (first run may take a few minutes)...")
        await cls._embedding_adapter.embed(["warmup"])
        logger.info("Embedding model ready")

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
                    "host": settings.chroma_host,
                    "port": settings.chroma_port,
                },
            },
        )

        # RAGAnything does not eagerly construct its internal LightRAG instance.
        # Query requests call rag.aquery() directly, so we must initialize the
        # underlying LightRAG object during application startup instead of waiting
        # for the first document-processing path to do it implicitly.
        init_result = await cls._rag_instance._ensure_lightrag_initialized()
        if not init_result.get("success"):
            raise RuntimeError(init_result.get("error", "Failed to initialize LightRAG"))

        if settings.rag_skip_entity_extraction:
            async def _skip_extract_entities(_self, chunk, pipeline_status=None, pipeline_status_lock=None):
                return []

            cls._rag_instance.lightrag._process_extract_entities = _skip_extract_entities.__get__(
                cls._rag_instance.lightrag,
                type(cls._rag_instance.lightrag),
            )
            logger.warning(
                "RAG skip entity extraction is enabled; indexing uses chunk vectors only."
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

    @classmethod
    def _ensure_libreoffice_in_path(cls) -> None:
        libreoffice_program_dir = "C:\\Program Files\\LibreOffice\\program"
        soffice = os.path.join(libreoffice_program_dir, "soffice.exe")
        if not os.path.exists(soffice):
            return

        current_path = os.environ.get("PATH", "")
        path_parts = current_path.split(os.pathsep) if current_path else []
        if libreoffice_program_dir not in path_parts:
            os.environ["PATH"] = f"{libreoffice_program_dir}{os.pathsep}{current_path}"
            logger.info("Added LibreOffice to PATH for current backend process")
