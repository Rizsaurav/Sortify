# Unit Tests for Sortify Embedding Service

## Overview
This directory contains comprehensive unit tests for the Sortify Embedding Service core functionality.

## Test Structure

```
unit_tests/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── test_embedding_service.py    (18 tests)
│   ├── test_chunking_service.py     (27 tests)
│   └── test_database_service.py     (27 tests)
└── README.md (this file)
```

## Running Tests

### Prerequisites
```bash
# Make sure you're in the embedding directory
cd /home/abheekp/sortify/embedding

# No additional dependencies needed - uses Python's built-in unittest
```

### Run All Tests
```bash
# Discover and run all tests in unit_tests/core/
python -m unittest discover unit_tests/core -v
```

Expected output:
```
Ran 72 tests in 0.136s
OK (skipped=1)
```

### Run Individual Test Files

**Test Embedding Service:**
```bash
python -m unittest unit_tests/core/test_embedding_service.py -v
```

**Test Chunking Service:**
```bash
python -m unittest unit_tests/core/test_chunking_service.py -v
```

**Test Database Service:**
```bash
python -m unittest unit_tests/core/test_database_service.py -v
```

### Run Specific Test Class
```bash
python -m unittest unit_tests.core.test_embedding_service.TestEmbeddingService -v
```

### Run Specific Test Method
```bash
python -m unittest unit_tests.core.test_embedding_service.TestEmbeddingService.test_encode_single_text -v
```

## Test Coverage

### 1. EmbeddingService Tests (18 tests)
- Model initialization and configuration
- Single and batch text encoding
- Query vs document encoding
- Instruction prompt handling
- Error handling
- Singleton pattern

### 2. ChunkingService Tests (27 tests)
- Text chunking with various sizes
- Sentence splitting logic
- Chunk overlap functionality
- Preprocessing integration
- Edge cases (empty text, short text, long sentences)
- Metadata generation

### 3. DatabaseService Tests (27 tests)
- Database connection
- Document CRUD operations
- Chunk operations
- Category operations
- NumPy array conversion
- Embedding parsing

## Testing Approach

All tests use **mocking** to avoid external dependencies:
- No actual model downloads required
- No database connections needed
- Fast execution (< 1 second for all tests)

## Test Quality Standards

✅ Each test follows AAA pattern (Arrange-Act-Assert)
✅ Descriptive test names explain purpose
✅ Comprehensive docstrings
✅ Single responsibility per test
✅ All edge cases covered

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No external dependencies
- Deterministic results
- Fast execution
- Clear pass/fail status

## Troubleshooting

### Import Errors
If you get import errors, make sure you're running from the `embedding/` directory:
```bash
cd /home/abheekp/sortify/embedding
python -m unittest discover unit_tests/core -v
```

### Path Issues
Tests use `sys.path.insert()` to find modules. If you move files, update paths in test files.

## Contributing

When adding new features to core/:
1. Create corresponding test file in unit_tests/core/
2. Follow existing test structure
3. Use mocking for external dependencies
4. Aim for 100% coverage of public methods
5. Test both success and error paths

## SOLID Principles

These tests demonstrate SOLID principles:
- **SRP:** Each test class tests one service
- **OCP:** Mocking allows extension without modification
- **DIP:** Tests verify loose coupling via dependency injection

## Assignment Deliverables

For the SOLID assignment, see:
- `SOLID_Analysis_Abheek_Pradhan.md` - Complete SOLID analysis
- `TEST_SUMMARY.md` - Test execution summary

---

**Created by:** Abheek Pradhan
**Date:** November 5, 2025
