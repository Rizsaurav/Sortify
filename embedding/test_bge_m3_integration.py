#!/usr/bin/env python3
"""
Test script to verify BGE-M3 embedding model integration.
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.embedding_service import get_embedding_service
from settings import get_settings, get_model_config


def test_embedding_service():
    """Test that BGE-M3 loads and generates embeddings correctly."""

    print("=" * 60)
    print("BGE-M3 Integration Test")
    print("=" * 60)

    # 1. Check configuration
    print("\n1. Checking configuration...")
    settings = get_settings()
    model_config = get_model_config()

    print(f"   Embedding model: {settings.embedding_model}")
    print(f"   Expected dimension: {settings.embedding_dimension}")
    print(f"   Device: {model_config.device}")

    assert settings.embedding_model == "BAAI/bge-m3", "Model should be BGE-M3"
    assert settings.embedding_dimension == 1024, "Dimension should be 1024"
    print("   ✓ Configuration correct")

    # 2. Load embedding service
    print("\n2. Loading embedding service...")
    try:
        service = get_embedding_service()
        print(f"   ✓ Service loaded successfully")
        print(f"   Model: {service.model_name}")
        print(f"   Dimension: {service.embedding_dim}")
    except Exception as e:
        print(f"   ✗ Failed to load service: {e}")
        return False

    # 3. Test single document encoding
    print("\n3. Testing document encoding...")
    test_doc = "Machine learning is a subset of artificial intelligence."
    try:
        doc_embedding = service.encode_document(test_doc)
        print(f"   Input: '{test_doc}'")
        print(f"   Output shape: {doc_embedding.shape}")
        print(f"   Output dtype: {doc_embedding.dtype}")
        print(f"   First 5 values: {doc_embedding[:5]}")

        assert doc_embedding.shape == (1024,), f"Expected (1024,), got {doc_embedding.shape}"
        assert isinstance(doc_embedding, np.ndarray), "Should return numpy array"
        print("   ✓ Document encoding works")
    except Exception as e:
        print(f"   ✗ Document encoding failed: {e}")
        return False

    # 4. Test query encoding
    print("\n4. Testing query encoding...")
    test_query = "What is machine learning?"
    try:
        query_embedding = service.encode_query(test_query)
        print(f"   Input: '{test_query}'")
        print(f"   Output shape: {query_embedding.shape}")
        print(f"   First 5 values: {query_embedding[:5]}")

        assert query_embedding.shape == (1024,), f"Expected (1024,), got {query_embedding.shape}"
        print("   ✓ Query encoding works")
    except Exception as e:
        print(f"   ✗ Query encoding failed: {e}")
        return False

    # 5. Test batch encoding
    print("\n5. Testing batch encoding...")
    test_texts = [
        "Python is a programming language.",
        "Natural language processing is a field of AI.",
        "Deep learning uses neural networks."
    ]
    try:
        batch_embeddings = service.encode_batch(test_texts)
        print(f"   Input: {len(test_texts)} texts")
        print(f"   Output shape: {batch_embeddings.shape}")

        assert batch_embeddings.shape == (3, 1024), f"Expected (3, 1024), got {batch_embeddings.shape}"
        print("   ✓ Batch encoding works")
    except Exception as e:
        print(f"   ✗ Batch encoding failed: {e}")
        return False

    # 6. Test semantic similarity
    print("\n6. Testing semantic similarity...")
    try:
        similar_text = "ML is part of AI."
        dissimilar_text = "The weather is sunny today."

        similar_emb = service.encode_document(similar_text)
        dissimilar_emb = service.encode_document(dissimilar_text)

        # Cosine similarity
        sim_to_doc = np.dot(doc_embedding, similar_emb) / (
            np.linalg.norm(doc_embedding) * np.linalg.norm(similar_emb)
        )
        dissim_to_doc = np.dot(doc_embedding, dissimilar_emb) / (
            np.linalg.norm(doc_embedding) * np.linalg.norm(dissimilar_emb)
        )

        print(f"   Similarity (similar text): {sim_to_doc:.4f}")
        print(f"   Similarity (dissimilar text): {dissim_to_doc:.4f}")

        assert sim_to_doc > dissim_to_doc, "Similar text should have higher similarity"
        print("   ✓ Semantic similarity works correctly")
    except Exception as e:
        print(f"   ✗ Semantic similarity test failed: {e}")
        return False

    # 7. Test model info
    print("\n7. Checking model info...")
    try:
        info = service.get_model_info()
        print(f"   Model name: {info['model_name']}")
        print(f"   Dimension: {info['dimension']}")
        print(f"   Device: {info['device']}")
        print(f"   Max seq length: {info['max_seq_length']}")
        print("   ✓ Model info accessible")
    except Exception as e:
        print(f"   ✗ Failed to get model info: {e}")
        return False

    print("\n" + "=" * 60)
    print("All tests passed! BGE-M3 integration successful.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_embedding_service()
    sys.exit(0 if success else 1)
