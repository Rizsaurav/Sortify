# Unit Testing Plan for Sortify - Configuration & API Layer

## Overview

Unit testing strategy for three core components: settings management, API models validation, and RAG service functionality.

## Files in This Directory

1. **test_settings.py** - Configuration management (7 tests)
2. **test_api_models.py** - Pydantic API models validation (45 tests)
3. **test_api_service.py** - RAG Service API integration (14 tests)

---

## 1. Settings & Configuration Tests (7 tests)

**Target:** `embedding/settings/settings.py` - `Settings`, `ModelConfig`, `DatabaseConfig`

**Test Cases:**

1. `initialization_with_required_env_vars` - Validates all required env vars and defaults
2. `missing_required_env_var_raises_error` - Tests ValueError for missing GOOGLE_API_KEY
3. `custom_env_var_overrides` - Verifies type conversion (int, float, bool)
4. `cors_origins_parsing` - Tests comma-separated list parsing with whitespace trim
5. `singleton_pattern` - Ensures get_settings() returns same instance
6. `model_config_properties` - Tests ModelConfig exposes correct settings
7. `database_config_properties` - Tests DatabaseConfig exposes correct credentials

---

## 2. API Models Validation Tests (45 tests)

**Target:** `embedding/models/api_models.py` - All Pydantic models

**Models Tested:**

- **QuestionRequest/Response** (10 tests)
  - Valid creation with defaults/custom values
  - Missing required fields validation
  - Optional fields as None
  - Model serialization

- **SearchRequest/SearchResult/SearchResponse** (15 tests)
  - Query validation
  - Empty/multiple results handling
  - Nested object serialization

- **DocumentUploadResponse** (5 tests)
  - Status values (queued, duplicate, error)
  - Optional doc_id/task_id fields

- **TaskStatusResponse** (5 tests)
  - Status values (pending, processing, completed, failed)
  - Error field population

- **ProcessingStatus** (5 tests)
  - loaded_from_cache default
  - Optional processing_time
  - ready flag variations

- **HealthResponse** (5 tests)
  - Healthy/unhealthy states
  - Version string formats

---

## 3. RAG Service API Tests (14 tests)

**Target:** `embedding/api_service.py` - `RAGService`

**Test Cases:**

**Initialization (5 tests):**
1. `initialization_creates_required_components` - Verifies rag, doc_manager, supabase creation
2. `initialization_without_config_uses_default` - Tests default config from environment
3. `initialize_success_updates_service_state` - Tests successful document processing
4. `initialize_handles_processing_errors` - Tests error handling
5. `ask_question_when_not_ready_raises_exception` - Tests 503 HTTPException

**Question Answering (5 tests):**
6. `ask_question_returns_valid_response` - Tests answer, sources, chunks_used
7. `ask_question_with_fallback_used` - Tests fallback scenario
8. `ask_question_handles_rag_errors` - Tests 500 HTTPException
9. `ask_question_passes_top_k_parameter` - Verifies parameter passing
10. `ask_question_async_execution` - Tests async via event loop

**Document Search (4 tests):**
11. `search_documents_returns_valid_results` - Tests result structure
12. `search_documents_when_not_ready_raises_exception` - Tests 503 HTTPException
13. `search_documents_with_empty_results` - Tests empty list handling
14. `search_documents_passes_parameters_correctly` - Verifies top_k, threshold

---

## Test Execution

### Quick Start

```bash
# Navigate to test directory
cd /Users/shivendrabhagat/CS\ TXST/Sortify/sortify/tests/shivendra-tests

# Activate virtual environment
source ../../embedding/venv/bin/activate

# Run individual tests
python3 test_settings.py -v
python3 test_api_models.py -v
python3 test_api_service.py -v

# Generate HTML reports
pytest test_settings.py --html=settings-results.html --self-contained-html
pytest test_api_models.py --html=api-models-results.html --self-contained-html
pytest test_api_service.py --html=api-service-results.html --self-contained-html

# Run all tests
python3 -m unittest discover -v
```

### Generated Files

```
sortify/tests/shivendra-tests/
├── UNIT_TEST_PLAN.md
├── test_settings.py
├── test_api_models.py
├── test_api_service.py
├── settings-results.html
├── api-models-results.html
└── api-service-results.html
```

### Success Criteria

- **Total:** 66 unit tests (7 + 45 + 14)
- **Pass Rate:** 100%
- HTML reports generated for all test files
- Clean test output (no error logs)
- All Pydantic models validate correctly
- All async operations execute properly

### Mocked Dependencies

- `smart_sorter.SmartSorter`
- `rag_system.FastRAG`
- `config.RAGConfig`
- `document_manager.DocumentManager`
- `supabase.create_client`
