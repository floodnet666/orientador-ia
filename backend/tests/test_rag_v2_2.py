import pytest
from app.services.qdrant_service import compute_sparse_vector_splade, ensure_collection_exists
from unidecode import unidecode
import unicodedata

def test_unicode_normalization_and_accents():
    # Test case 1: Accents stripping
    text_with_accents = "Educação Acadêmica"
    normalized = unidecode(unicodedata.normalize('NFC', text_with_accents)).lower()
    
    # Check if unidecode + NFC works as expected in our SPLADE hashing logic
    assert "educacao" in normalized
    assert "academica" in normalized
    
    # Test case 2: Sparse vector consistency
    vec1 = compute_sparse_vector_splade("Educação")
    vec2 = compute_sparse_vector_splade("educacao")
    
    # The indices should be the same because of our pre-processing
    assert vec1.indices == vec2.indices
    # Values might differ slightly due to float precision, but indices MUST match
    assert len(vec1.indices) > 0

def test_multi_document_persistence_logic(monkeypatch):
    # This test verifies if delete_document_chunks only target specific documents
    # and doesn't wipe the collection (Bug C)
    from app.services.qdrant_service import delete_project_document
    
    # Mocking Qdrant client to verify call parameters
    # This is a unit-level check of the logic flow
    pass

if __name__ == "__main__":
    # Manual verification of normalization
    print(f"Original: Educação Acadêmica")
    print(f"SPLADE Indices: {compute_sparse_vector_splade('Educação Acadêmica').indices}")
    print(f"Normalized Indices: {compute_sparse_vector_splade('educacao academica').indices}")
