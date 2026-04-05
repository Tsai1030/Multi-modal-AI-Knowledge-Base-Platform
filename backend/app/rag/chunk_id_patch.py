from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from functools import wraps
from typing import Any, Callable

from lightrag.utils import compute_mdhash_id as _base_compute_mdhash_id

_CURRENT_DOC_ID: ContextVar[str | None] = ContextVar("current_chunk_doc_id", default=None)
_PATCHED = False


def _doc_aware_compute_mdhash_id(content: str, prefix: str = "") -> str:
    """Namespace chunk ids by document id to avoid cross-document collisions."""
    doc_id = _CURRENT_DOC_ID.get()
    if prefix == "chunk-" and doc_id:
        return _base_compute_mdhash_id(f"{doc_id}\n{content}", prefix=prefix)
    return _base_compute_mdhash_id(content, prefix=prefix)


@contextmanager
def scoped_doc_id(doc_id: str | None):
    token: Token[str | None] = _CURRENT_DOC_ID.set(doc_id)
    try:
        yield
    finally:
        _CURRENT_DOC_ID.reset(token)


def _wrap_async_doc_method(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    async def wrapper(self, *args: Any, **kwargs: Any):
        with scoped_doc_id(kwargs.get("doc_id")):
            return await fn(self, *args, **kwargs)

    return wrapper


def apply_chunk_id_patch() -> None:
    """Monkey-patch LightRAG/RAGAnything chunk hashing to include doc scope."""
    global _PATCHED
    if _PATCHED:
        return

    import lightrag.lightrag as lightrag_module
    import lightrag.operate as operate_module
    import lightrag.utils as utils_module
    import raganything.modalprocessors as modalprocessors_module
    import raganything.processor as processor_module
    from raganything import RAGAnything

    for module in (
        utils_module,
        lightrag_module,
        operate_module,
        processor_module,
        modalprocessors_module,
    ):
        module.compute_mdhash_id = _doc_aware_compute_mdhash_id

    RAGAnything.insert_content_list = _wrap_async_doc_method(RAGAnything.insert_content_list)
    RAGAnything.process_document_complete = _wrap_async_doc_method(RAGAnything.process_document_complete)
    RAGAnything.process_document_complete_lightrag_api = _wrap_async_doc_method(
        RAGAnything.process_document_complete_lightrag_api
    )

    _PATCHED = True
