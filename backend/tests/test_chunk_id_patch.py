import lightrag.lightrag as lightrag_module
import lightrag.operate as operate_module
import raganything.processor as processor_module

from app.rag.chunk_id_patch import apply_chunk_id_patch, scoped_doc_id


def test_chunk_hash_is_namespaced_by_doc_id():
    apply_chunk_id_patch()

    with scoped_doc_id("doc-a"):
        chunk_a = lightrag_module.compute_mdhash_id("same content", prefix="chunk-")
    with scoped_doc_id("doc-b"):
        chunk_b = lightrag_module.compute_mdhash_id("same content", prefix="chunk-")

    assert chunk_a != chunk_b


def test_non_chunk_hashes_are_unchanged_by_doc_scope():
    apply_chunk_id_patch()

    with scoped_doc_id("doc-a"):
        doc_hash_scoped = operate_module.compute_mdhash_id("same content", prefix="doc-")
    with scoped_doc_id("doc-b"):
        doc_hash_other = operate_module.compute_mdhash_id("same content", prefix="doc-")

    assert doc_hash_scoped == doc_hash_other


def test_patch_applies_to_raganything_modules_too():
    apply_chunk_id_patch()

    with scoped_doc_id("doc-a"):
        chunk_a = processor_module.compute_mdhash_id("same content", prefix="chunk-")
    with scoped_doc_id("doc-b"):
        chunk_b = processor_module.compute_mdhash_id("same content", prefix="chunk-")

    assert chunk_a != chunk_b
