# Unit Testing Plan for Sortify

## Overview

This document outlines unit testing strategy for three core components of the Sortify application. Tests focus on classes, methods, API calls, and complex code structures with proper assertion of fields and return objects.

## Files in This Directory

1. **UNIT_TEST_PLAN.md** (this file) - Test planning document
2. **test_document_service_unit.py** - Backend unit tests for DatabaseService class (10 tests)
3. **test_notifications_api_unit.py** - Backend unit tests for Notifications API (10 tests)
4. **test_embedding_service_unit.py** - Backend unit tests for EmbeddingService class (10 tests)

---

## 1. Document Service Unit Tests (Backend)

### Target Code
File: `embedding/services/database_service.py`
Class: `DatabaseService`

### Features to Test

#### Feature 1: Document CRUD Operations
**Methods Under Test:**
- `insert_document(content, user_id, metadata, embedding, cluster_id)`
- `get_document_by_id(document_id)`
- `update_document_cluster(document_id, cluster_id)`
- `delete_document(document_id)`
- `get_documents_by_user(user_id)`

**Test Cases:**

1. **Test: insert_document returns valid document ID**
   - Call `insert_document()` with valid parameters
   - Assert return value is UUID string
   - Query database directly to verify document exists
   - Assert all fields match input parameters
   - Verify `created_at` timestamp is set

2. **Test: insert_document validates required fields**
   - Call `insert_document()` without user_id
   - Assert raises ValueError or TypeError
   - Verify error message contains field name
   - Assert no document was created in database

3. **Test: get_document_by_id returns correct document object**
   - Insert test document
   - Call `get_document_by_id()` with document ID
   - Assert return is dict/object with expected keys
   - Verify `id`, `content`, `user_id`, `metadata`, `cluster_id` fields
   - Assert field values match inserted data

4. **Test: get_document_by_id returns None for invalid ID**
   - Call `get_document_by_id()` with non-existent UUID
   - Assert return value is None
   - Verify no exception is raised

5. **Test: update_document_cluster modifies cluster_id**
   - Insert document with cluster_id = 1
   - Call `update_document_cluster(doc_id, 5)`
   - Query document from database
   - Assert `cluster_id` field equals 5
   - Verify other fields remain unchanged

6. **Test: get_documents_by_user enforces user isolation**
   - Insert 3 documents for user A
   - Insert 2 documents for user B
   - Call `get_documents_by_user(user_a_id)`
   - Assert return is list of 3 items
   - Assert all items have `user_id` field matching user A
   - Verify user B's documents not in result

7. **Test: delete_document removes document**
   - Insert test document, capture ID
   - Call `delete_document(doc_id)`
   - Assert return value is True
   - Call `get_document_by_id(doc_id)`
   - Assert return is None

8. **Test: search_documents returns matching results**
   - Insert 5 documents with different content
   - Call `search_documents(user_id, "keyword")`
   - Assert return is list
   - Verify all items contain keyword in content field
   - Assert list length matches expected count

9. **Test: batch operations maintain atomicity**
   - Begin transaction
   - Insert 10 documents in loop
   - Force error on 8th document
   - Assert transaction rolls back
   - Verify 0 documents exist in database

10. **Test: category_history field is populated on update**
    - Insert document with cluster_id = 1
    - Update cluster_id to 5
    - Query document
    - Assert `category_history` field is JSONB array
    - Verify array contains entry with old_category_id = 1, new_category_id = 5
    - Assert entry has timestamp field

**Return Object Structure to Verify:**
```python
{
    'id': 'uuid-string',
    'content': 'string',
    'user_id': 'uuid-string',
    'metadata': {
        'filename': 'string',
        'type': 'string',
        'size': int
    },
    'embedding': [float] or None,
    'cluster_id': int or None,
    'category_history': [
        {
            'timestamp': 'ISO-8601',
            'old_category_id': int,
            'new_category_id': int,
            'action': 'string'
        }
    ],
    'created_at': 'ISO-8601',
    'updated_at': 'ISO-8601'
}
```

---

## 2. Notifications API Unit Tests (Backend)

### Target Code
File: `embedding/api/notifications_api.py`
Endpoints: `/notifications`, `/notifications/unread-count`, `/notifications/{document_id}/read/{notification_id}`

### Features to Test

#### Feature 2: Notifications API Endpoints
**API Calls Under Test:**
- `GET /notifications?user_id={uuid}&unread_only={bool}&limit={int}`
- `GET /notifications/unread-count?user_id={uuid}`
- `PATCH /notifications/{document_id}/read/{notification_id}`

**Test Cases:**

1. **Test: GET /notifications returns notification list**
   - Create test user and 5 documents with notifications
   - Call `GET /notifications?user_id={user_id}`
   - Assert response status is 200
   - Assert response body has keys: notifications, total, unread_count
   - Verify `notifications` is array of 5 items
   - Assert each item has id, document_id, title, message, type, is_read, created_at fields

2. **Test: GET /notifications filters by unread_only parameter**
   - Create 3 unread and 2 read notifications
   - Call `GET /notifications?user_id={user_id}&unread_only=true`
   - Assert response notifications array length is 3
   - Verify all items have `is_read: false`

3. **Test: GET /notifications respects limit parameter**
   - Create 20 notifications
   - Call `GET /notifications?user_id={user_id}&limit=10`
   - Assert response notifications array length is 10
   - Verify `total` field equals 20

4. **Test: GET /notifications enforces user isolation**
   - Create notifications for user A and user B
   - Call `GET /notifications?user_id={user_a_id}`
   - Assert all returned notifications belong to user A
   - Verify user B notifications not in response

5. **Test: GET /unread-count returns correct count**
   - Create 5 unread and 3 read notifications
   - Call `GET /notifications/unread-count?user_id={user_id}`
   - Assert response status is 200
   - Assert response body has `unread_count` field
   - Verify `unread_count` equals 5

6. **Test: PATCH /read marks notification as read**
   - Create unread notification
   - Call `PATCH /notifications/{doc_id}/read/{notif_id}`
   - Assert response status is 200
   - Query notification from database
   - Verify `is_read` field is true
   - Assert `read_at` timestamp is set

7. **Test: PATCH /read returns 404 for invalid notification**
   - Call `PATCH /notifications/invalid-id/read/invalid-id`
   - Assert response status is 404
   - Verify error message in response body

8. **Test: GET /notifications sorts by created_at descending**
   - Create notifications with different timestamps
   - Call `GET /notifications?user_id={user_id}`
   - Assert first item has most recent created_at
   - Verify items are in descending order

9. **Test: POST trigger creates notification on category change**
   - Update document cluster_id via database
   - Call `GET /notifications?user_id={user_id}`
   - Assert new notification exists
   - Verify notification type is 'success'
   - Assert message contains category name

10. **Test: Notifications include metadata field**
    - Create notification with custom metadata
    - Call `GET /notifications?user_id={user_id}`
    - Assert notification object has `metadata` field
    - Verify metadata contains expected keys
    - Assert metadata values are correct type

**Response Object Structure to Verify:**
```json
{
  "notifications": [
    {
      "id": "uuid-string",
      "document_id": "uuid-string",
      "filename": "string",
      "title": "string",
      "message": "string",
      "type": "success|error|info|warning",
      "metadata": {
        "action": "string",
        "category_name": "string"
      },
      "is_read": boolean,
      "created_at": "ISO-8601",
      "read_at": "ISO-8601|null"
    }
  ],
  "total": integer,
  "unread_count": integer
}
```

---

## 3. Embedding Service Unit Tests (Backend)

### Target Code
File: `embedding/core/embedding_service.py`
Class: `EmbeddingService`

### Features to Test

#### Feature 3: Embedding Generation Operations
**Methods Under Test:**
- `encode(texts, batch_size, normalize, use_instruction)`
- `encode_query(query)`
- `encode_document(document)`
- `encode_batch(texts, batch_size)`
- `get_dimension()`
- `get_model_info()`

**Test Cases:**

1. **Test: encode returns numpy array with correct shape**
   - Call `encode()` with single text
   - Assert return is numpy array
   - Verify shape is (1024,) for single text

2. **Test: encode_single_text returns 1D array**
   - Encode single text string
   - Assert ndim equals 1
   - Verify length matches embedding dimension

3. **Test: encode_batch returns 2D array**
   - Encode list of 3 texts
   - Assert shape is (3, 1024)
   - Verify ndim equals 2

4. **Test: encode_query uses instruction**
   - Call `encode_query()` with query text
   - Verify instruction prompt is applied
   - Assert embedding shape is correct

5. **Test: encode_document does not use instruction**
   - Call `encode_document()` with document text
   - Verify no instruction is prepended
   - Assert embedding generated correctly

6. **Test: normalize embeddings to unit length**
   - Generate embedding with normalize=True
   - Calculate L2 norm
   - Assert norm is close to 1.0

7. **Test: get_dimension returns correct value**
   - Call `get_dimension()`
   - Assert return value is 1024
   - Verify return type is int

8. **Test: get_model_info returns dict with required fields**
   - Call `get_model_info()`
   - Assert dict contains model_name, dimension, device
   - Verify all values have correct types

9. **Test: batch processing maintains input order**
   - Encode batch of texts
   - Verify output count matches input count
   - Assert order is preserved

10. **Test: singleton pattern returns same instance**
    - Call `get_embedding_service()` twice
    - Verify both calls return same object instance
    - Assert instance IDs are equal

**Return Object Structure to Verify:**

```python
# Single embedding
np.ndarray: shape (1024,), dtype float32

# Batch embeddings
np.ndarray: shape (n, 1024), dtype float32

# Model info
{
    'model_name': str,
    'dimension': int,
    'device': str,
    'max_seq_length': int
}
```

---

## Test Execution Requirements

### Framework and Tools

**Backend (Python):**
- Framework: `pytest`
- Coverage: `pytest-cov`
- Mocking: `pytest-mock`, `unittest.mock`
- Fixtures: pytest fixtures for setup/teardown

### Test Execution Commands

```bash
# Navigate to test directory
cd /Users/saurav/Desktop/Sortify/BitSortify/sortify/tests/saurav-tests

# Run individual tests
python test_document_service_unit.py
python test_notifications_api_unit.py
python test_embedding_service_unit.py

# Or with pytest
pytest test_document_service_unit.py -v --html=document-service-results.html --self-contained-html
pytest test_notifications_api_unit.py -v --html=notifications-api-results.html --self-contained-html
pytest test_embedding_service_unit.py -v --html=embedding-service-results.html --self-contained-html
```

### Generated Reports

Each test generates a self-contained HTML report in the same directory:

```
sortify/tests/saurav-tests/
├── UNIT_TEST_PLAN.md
├── test_document_service_unit.py
├── test_notifications_api_unit.py
├── test_embedding_service_unit.py
├── document-service-results.html
├── notifications-api-results.html
└── embedding-service-results.html
```

### Report Contents

Each HTML report contains:
- Test summary (passed/failed/skipped counts)
- Execution time
- Environment information (Python version, platform, packages)
- Detailed test results for each test case
- Timestamp of test execution

### Success Criteria

- Total: 32 unit tests (10 + 12 + 10)
- All tests must pass
- HTML reports generated for all test files
- Reports show execution timestamp and environment details
