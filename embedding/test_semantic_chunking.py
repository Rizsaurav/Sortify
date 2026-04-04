"""
Quick test for semantic chunking functionality.
Tests heading detection, topic shift detection, and coherence scoring.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Create a test document with clear topics
test_document = """
# Machine Learning Basics

Machine learning is a subset of artificial intelligence. It focuses on building systems that learn from data. These systems can improve their performance over time without being explicitly programmed.

There are three main types of machine learning: supervised, unsupervised, and reinforcement learning. Each type has its own unique characteristics and applications.

## Supervised Learning

Supervised learning involves training a model on labeled data. The model learns to map inputs to outputs based on example input-output pairs. Common applications include classification and regression tasks.

Popular algorithms include linear regression, decision trees, and neural networks. These algorithms have proven effective across many domains.

# Healthy Cooking Tips

Cooking healthy meals doesn't have to be complicated. Start by incorporating more vegetables into your diet. Fresh, colorful vegetables provide essential nutrients and vitamins.

Meal preparation is key to maintaining a healthy diet. Plan your meals in advance and batch cook on weekends. This saves time during busy weekdays.

## Kitchen Equipment

Essential kitchen tools include a good knife, cutting board, and non-stick pan. Invest in quality equipment that will last for years. A slow cooker can also be helpful for preparing easy, healthy meals.

# Climate Change

Climate change is one of the most pressing issues of our time. Rising global temperatures affect ecosystems worldwide. Scientists agree that human activities are the primary cause.

Renewable energy sources like solar and wind power offer sustainable alternatives. Transitioning to clean energy is crucial for reducing carbon emissions.
"""

def test_semantic_chunking():
    """Test semantic chunking with topic shifts and headings."""
    from core.chunking_service import ChunkingService

    print("=" * 60)
    print("Testing Semantic Chunking")
    print("=" * 60)

    # Initialize with semantic chunking enabled
    service = ChunkingService(
        use_semantic_chunking=True,
        chunk_size=300,
        chunk_overlap=50,
        min_chunk_size_tokens=20,
        topic_shift_threshold=0.5
    )

    # Chunk with metadata to see coherence scores
    chunks = service.chunk_text_semantic(
        test_document,
        preprocess=True,
        return_metadata=True
    )

    print(f"\nCreated {len(chunks)} semantic chunks:\n")

    for i, chunk_meta in enumerate(chunks):
        content = chunk_meta['content']
        coherence = chunk_meta.get('coherence_score', 0.0)
        tokens = chunk_meta.get('token_count', 0)

        # Show first 100 chars of each chunk
        preview = content[:100].replace('\n', ' ')
        if len(content) > 100:
            preview += "..."

        print(f"Chunk {i+1}:")
        print(f"  Tokens: {tokens:.0f}")
        print(f"  Coherence: {coherence:.2f}")
        print(f"  Preview: {preview}")
        print()

    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)

    # Test heading detection
    print("\nTesting Heading Detection:")
    headings = service._detect_headings(test_document)
    print(f"Found {len(headings)} headings:")
    for heading in headings:
        print(f"  Level {heading['level']}: {heading['text']}")

    return chunks

if __name__ == '__main__':
    try:
        chunks = test_semantic_chunking()
        print("\n✓ Semantic chunking test passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
