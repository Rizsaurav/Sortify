# Hierarchical Chunking

## Overview

Hierarchical chunking creates a parent-child structure where:
- **Parent chunks** (~2000 tokens) represent larger sections/topics providing broader context
- **Child chunks** (~1000 tokens) are smaller units enabling precise retrieval

This approach improves RAG quality by:
1. Retrieving precise child chunks for accuracy
2. Providing parent context for comprehensive understanding
3. Maintaining semantic relationships across document structure

## Configuration

Add to your `.env` file:

```bash
# Enable hierarchical chunking (default: false)
USE_HIERARCHICAL_CHUNKING=true

# Parent chunk size in tokens (default: 2000)
PARENT_CHUNK_SIZE=2000

# Child chunk size in tokens (default: 1000)
CHILD_CHUNK_SIZE=1000
```

## How It Works

### 1. Document Processing

When a document is uploaded:
1. Creates parent chunks using semantic boundaries (sections, topics)
2. For each parent, creates child chunks from its content
3. Stores both with parent-child relationships in metadata

### 2. Chunk Structure

**Child Chunk Metadata:**
```json
{
  "chunk_type": "child",
  "parent_id": "parent_0",
  "parent_content": "Full parent chunk content...",
  "token_count": 950,
  "coherence_score": 0.85,
  "relative_position": 0.25
}
```

**Parent Chunk Metadata:**
```json
{
  "chunk_type": "parent",
  "child_count": 3,
  "token_count": 1980,
  "coherence_score": 0.92
}
```

### 3. Retrieval Strategy

When querying:
1. RAG retrieves child chunks (precise matches)
2. Parent content is available in metadata for expanded context
3. LLM gets both focused chunk and broader section context

## Example

```python
from core.chunking_service import ChunkingService

service = ChunkingService()

# Create hierarchical chunks
result = service.chunk_text_hierarchical(
    document_text,
    parent_chunk_size=2000,
    child_chunk_size=1000
)

# Access chunks
parent_chunks = result['parent_chunks']
child_chunks = result['child_chunks']
hierarchy = result['hierarchy']  # Maps parent_id -> [child_ids]
```

## Testing

Run the test script:
```bash
python test_hierarchical_chunking.py
```

## Benefits

1. **Better Context**: Child chunks include parent content reference
2. **Semantic Coherence**: Parents respect topic boundaries
3. **Flexible Retrieval**: Can retrieve at child or parent level
4. **Quality Metrics**: Coherence scores for both levels

## When to Use

**Recommended for:**
- Long documents (>5000 tokens)
- Multi-topic documents
- Academic papers, reports, documentation
- When context is critical for understanding

**Not needed for:**
- Short documents (<2000 tokens)
- Simple Q&A content
- Already well-chunked data

## Notes

- Hierarchical chunking is disabled by default (opt-in)
- Increases storage by storing both parent and child chunks
- Provides better RAG quality for complex documents
- Compatible with semantic chunking features
