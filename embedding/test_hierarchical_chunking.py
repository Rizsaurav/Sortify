"""
Test for hierarchical chunking functionality.
Tests parent-child chunk relationships and metadata.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Create a test document with multiple sections
test_document = """
# Introduction to Artificial Intelligence

Artificial intelligence (AI) is the simulation of human intelligence processes by machines, especially computer systems. These processes include learning, reasoning, and self-correction. AI has become an essential part of the technology industry.

The field of AI research was founded in 1956. Since then, it has experienced several waves of optimism, followed by disappointment and the loss of funding, followed by new approaches, success and renewed funding.

## Applications of AI

AI is used in healthcare for diagnosing diseases and creating treatment plans. Machine learning algorithms can analyze medical images to detect cancers and other conditions with high accuracy.

In finance, AI helps in fraud detection, algorithmic trading, and customer service through chatbots. Banks use AI systems to monitor transactions in real-time and flag suspicious activities.

Transportation has been revolutionized by self-driving cars. Companies like Tesla and Waymo are at the forefront of autonomous vehicle technology.

## Types of AI Systems

There are several categories of AI systems. Narrow AI is designed for specific tasks like voice recognition or image classification. This is the most common type of AI in use today.

General AI would have the ability to understand, learn, and apply intelligence across a wide range of tasks, similar to human capabilities. This remains largely theoretical.

Superintelligent AI is a hypothetical future system that would surpass human intelligence in all aspects. This concept raises important ethical and safety considerations.

# Machine Learning Fundamentals

Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed. It focuses on the development of computer programs that can access data and use it to learn for themselves.

## Supervised Learning

Supervised learning uses labeled datasets to train algorithms. The algorithm learns from the training data and applies this learning to new, unseen data. Common applications include email spam filters and image recognition.

Decision trees, random forests, and neural networks are popular supervised learning algorithms. Each has strengths and weaknesses depending on the problem domain.

## Unsupervised Learning

Unsupervised learning finds hidden patterns in unlabeled data. Clustering algorithms like K-means and hierarchical clustering are commonly used. These techniques are useful for customer segmentation and anomaly detection.

Dimensionality reduction techniques like PCA help in visualizing high-dimensional data. This is particularly useful in exploratory data analysis.

# Future of AI

The future of AI holds tremendous potential and challenges. Ethical considerations around bias, privacy, and job displacement need to be addressed. Responsible AI development is crucial.

Quantum computing may revolutionize AI capabilities by enabling faster processing of complex algorithms. This could accelerate breakthroughs in drug discovery, climate modeling, and more.

Human-AI collaboration will likely define the next era of technological advancement. Rather than replacing humans, AI systems will augment human capabilities and decision-making.
"""

def test_hierarchical_chunking():
    """Test hierarchical chunking with parent-child relationships."""
    from core.chunking_service import ChunkingService

    print("=" * 70)
    print("Testing Hierarchical Chunking")
    print("=" * 70)

    # Initialize chunking service
    service = ChunkingService()

    # Create hierarchical chunks
    result = service.chunk_text_hierarchical(
        test_document,
        preprocess=True,
        parent_chunk_size=2000,
        child_chunk_size=1000
    )

    parent_chunks = result['parent_chunks']
    child_chunks = result['child_chunks']
    hierarchy = result['hierarchy']

    print(f"\nHierarchical Structure:")
    print(f"  Parent chunks: {len(parent_chunks)}")
    print(f"  Child chunks: {len(child_chunks)}")
    print(f"  Average children per parent: {len(child_chunks)/len(parent_chunks):.1f}")
    print()

    # Display parent-child relationships
    print("Parent-Child Relationships:")
    print("-" * 70)

    for parent in parent_chunks:
        parent_id = parent['id']
        parent_tokens = parent.get('token_count', 0)
        parent_coherence = parent.get('coherence_score', 0.0)
        child_count = parent.get('child_count', 0)

        # Get preview of parent content
        parent_preview = parent['content'][:80].replace('\n', ' ')
        if len(parent['content']) > 80:
            parent_preview += "..."

        print(f"\n{parent_id}:")
        print(f"  Tokens: {parent_tokens:.0f}")
        print(f"  Coherence: {parent_coherence:.2f}")
        print(f"  Children: {child_count}")
        print(f"  Preview: {parent_preview}")

        # Show children
        child_ids = hierarchy.get(parent_id, [])
        for child_id in child_ids:
            # Find child chunk
            child = next((c for c in child_chunks if c['id'] == child_id), None)
            if child:
                child_tokens = child.get('token_count', 0)
                child_preview = child['content'][:60].replace('\n', ' ')
                if len(child['content']) > 60:
                    child_preview += "..."
                print(f"    ↳ {child_id}: {child_tokens:.0f} tokens")
                print(f"      {child_preview}")

    print()
    print("=" * 70)
    print("Sample Child Chunk with Parent Context:")
    print("=" * 70)

    if child_chunks:
        sample_child = child_chunks[0]
        print(f"\nChild ID: {sample_child['id']}")
        print(f"Tokens: {sample_child.get('token_count', 0):.0f}")
        print(f"Parent ID: {sample_child.get('parent_id', 'N/A')}")
        print(f"\nChild Content:")
        print("-" * 70)
        print(sample_child['content'][:300])
        print()
        print("\nParent Context (for broader understanding):")
        print("-" * 70)
        parent_context = sample_child.get('parent_content', 'N/A')
        if parent_context != 'N/A':
            print(parent_context[:300])
        print()

    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)

    return result

if __name__ == '__main__':
    try:
        result = test_hierarchical_chunking()
        print("\n✓ Hierarchical chunking test passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
