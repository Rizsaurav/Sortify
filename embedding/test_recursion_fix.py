#!/usr/bin/env python3
"""
Test script to verify the chunking recursion fix.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.chunking_service import ChunkingService
from settings import get_settings

def test_semantic_chunking_without_paragraphs():
    """
    Test semantic chunking with text that has no paragraph breaks.
    This was causing the infinite recursion.
    """
    # Create chunking service with semantic chunking enabled
    settings = get_settings()
    chunking_service = ChunkingService(
        use_semantic_chunking=True,
        topic_shift_threshold=0.5
    )

    # Test text without paragraph breaks (this was causing the recursion)
    test_text = """
    This is a test document. It has multiple sentences. But it doesn't have any paragraph breaks.
    All the text is in a single line or separated by single newlines. This should trigger the
    fallback to sentence-based chunking. Previously this would cause infinite recursion.
    Now it should work correctly by disabling semantic chunking when falling back.
    Let's add more content to make it long enough to chunk. More text here. And even more text.
    We need enough content to create multiple chunks. Keep adding sentences. One more sentence.
    Another sentence here. And another. Keep going. More content needed. Almost there.
    Just a bit more text to make sure we have enough for proper chunking behavior.
    """

    print("Testing semantic chunking with text that has no paragraphs...")
    print(f"Use semantic chunking: {chunking_service.use_semantic_chunking}")
    print(f"Text length: {len(test_text)} characters")
    print()

    try:
        # This should NOT cause infinite recursion
        chunks = chunking_service.chunk_text(test_text)

        print(f"✓ SUCCESS! Created {len(chunks)} chunks without recursion error")
        print()

        for i, chunk in enumerate(chunks, 1):
            preview = chunk[:100].replace('\n', ' ').strip()
            print(f"Chunk {i}: {preview}...")

        return True

    except RecursionError as e:
        print(f"✗ FAILED! Recursion error occurred: {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED! Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_semantic_chunking_with_paragraphs():
    """
    Test semantic chunking with text that has paragraph breaks.
    This should work normally.
    """
    chunking_service = ChunkingService(
        use_semantic_chunking=True,
        topic_shift_threshold=0.5
    )

    test_text = """
    First paragraph with some content. This paragraph discusses topic A.
    It has multiple sentences about topic A. More details about A.

    Second paragraph discussing a different topic B. This is about B.
    More information about topic B goes here. Additional B content.

    Third paragraph about topic C. Content about C starts here.
    More details about topic C. Even more C information.
    """

    print("\nTesting semantic chunking with text that has paragraphs...")
    print(f"Text length: {len(test_text)} characters")
    print()

    try:
        chunks = chunking_service.chunk_text(test_text)
        print(f"✓ SUCCESS! Created {len(chunks)} chunks")
        print()

        for i, chunk in enumerate(chunks, 1):
            preview = chunk[:80].replace('\n', ' ').strip()
            print(f"Chunk {i}: {preview}...")

        return True

    except Exception as e:
        print(f"✗ FAILED! Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Chunking Service - Recursion Fix")
    print("=" * 70)
    print()

    # Run tests
    test1_pass = test_semantic_chunking_without_paragraphs()
    test2_pass = test_semantic_chunking_with_paragraphs()

    print()
    print("=" * 70)
    if test1_pass and test2_pass:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)
