from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import chromadb
from lightrag.base import BaseVectorStorage


@dataclass
class ChromaVectorDBStorage(BaseVectorStorage):
    """ChromaDB-backed vector storage implementing LightRAG's BaseVectorStorage interface.

    Register into LightRAG's storage registry via RAGEngine.initialize() so that
    LightRAG can resolve it by name: vector_storage="ChromaVectorDBStorage".
    """

    host: str = field(default="localhost")
    port: int = field(default=8001)

    def __post_init__(self) -> None:
        self._validate_embedding_func()

        # Pull connection params from global_config when available
        self.host = self.global_config.get("chroma_host", self.host)
        self.port = int(self.global_config.get("chroma_port", self.port))

        self._client: chromadb.AsyncHttpClient | None = None
        self._collection: chromadb.AsyncCollection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Connect to ChromaDB and obtain (or create) the collection for this namespace."""
        self._client = await chromadb.AsyncHttpClient(host=self.host, port=self.port)
        collection_name = self._collection_name()
        self._collection = await self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def index_done_callback(self) -> None:
        """ChromaDB persists immediately on every write; no flush needed."""

    async def drop(self) -> dict[str, str]:
        """Delete the entire collection from ChromaDB."""
        try:
            if self._client:
                await self._client.delete_collection(self._collection_name())
                self._collection = None
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        """Insert or update vectors.

        Expected data format (LightRAG convention):
            { "<id>": { "content": str, "embedding": list[float], **meta } }
        """
        if not data or self._collection is None:
            return

        ids: list[str] = []
        embeddings: list[list[float]] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        texts_to_embed: list[str] = []
        ids_needing_embed: list[str] = []

        for doc_id, payload in data.items():
            ids.append(doc_id)
            documents.append(payload.get("content", ""))
            meta = {k: v for k, v in payload.items() if k not in ("content", "embedding")}
            metadatas.append(meta)

            if "embedding" in payload and payload["embedding"]:
                embeddings.append(payload["embedding"])
            else:
                texts_to_embed.append(payload.get("content", ""))
                ids_needing_embed.append(doc_id)
                embeddings.append([])  # placeholder

        # Compute missing embeddings
        if texts_to_embed:
            computed = await self.embedding_func(texts_to_embed)
            for i, doc_id in enumerate(ids_needing_embed):
                idx = ids.index(doc_id)
                embeddings[idx] = computed[i]

        await self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def query(
        self,
        query: str,
        top_k: int,
        query_embedding: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        if self._collection is None:
            return []

        if query_embedding is None:
            query_embedding = (await self.embedding_func([query]))[0]

        results = await self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        output: list[dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
            item: dict[str, Any] = {"id": doc_id, "content": doc, **meta}
            # LightRAG expects a similarity score (higher = better); convert cosine distance
            item["distance"] = 1.0 - dist
            output.append(item)

        return output

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        if self._collection is None:
            return None
        result = await self._collection.get(ids=[id], include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        return {"id": id, "content": result["documents"][0], **result["metadatas"][0]}

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        if self._collection is None:
            return []
        result = await self._collection.get(ids=ids, include=["documents", "metadatas"])
        return [
            {"id": doc_id, "content": doc, **meta}
            for doc_id, doc, meta in zip(
                result["ids"], result["documents"], result["metadatas"]
            )
        ]

    async def get_vectors_by_ids(self, ids: list[str]) -> dict[str, list[float]]:
        if self._collection is None:
            return {}
        result = await self._collection.get(ids=ids, include=["embeddings"])
        return {
            doc_id: vec
            for doc_id, vec in zip(result["ids"], result["embeddings"])
        }

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, ids: list[str]) -> None:
        if self._collection is None:
            return
        await self._collection.delete(ids=ids)

    async def delete_entity(self, entity_name: str) -> None:
        """Delete entity by its stored entity_name metadata field."""
        if self._collection is None:
            return
        result = await self._collection.get(
            where={"entity_name": entity_name}, include=["documents"]
        )
        if result["ids"]:
            await self._collection.delete(ids=result["ids"])

    async def delete_entity_relation(self, entity_name: str) -> None:
        """Delete all relations involving this entity."""
        if self._collection is None:
            return
        result = await self._collection.get(
            where={"$or": [{"src_id": entity_name}, {"tgt_id": entity_name}]},
            include=["documents"],
        )
        if result["ids"]:
            await self._collection.delete(ids=result["ids"])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collection_name(self) -> str:
        suffix = self._generate_collection_suffix()
        base = f"{self.namespace}"
        if self.workspace:
            base = f"{self.workspace}_{base}"
        return f"{base}_{suffix}" if suffix else base
