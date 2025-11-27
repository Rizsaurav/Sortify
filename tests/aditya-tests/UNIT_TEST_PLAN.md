# Unit Testing Plan
**Course**: CS3388 - Software Engineering  
**Assignment**: Spring Assignment 14  
**Student**: Aaditya Baniya  
**Due Date**: November 26, 2025  
**Testing Framework**: pytest (Python)

---

## Project Overview
This testing plan covers unit tests for a FastAPI-based document management system with RAG (Retrieval-Augmented Generation) capabilities. The system handles document uploads, categorization, notifications, and question-answering features.

---

## Test 1: Document Upload API Endpoint

### Feature Under Test
**API Endpoint**: `POST /upload`  
**File**: `upload_api.py`  
**Function**: `upload_document()`

### Code Complexity
- Handles file upload with multiple file types (PDF, text, images)
- Performs duplicate detection
- Creates database records
- Generates unique filenames to avoid conflicts
- Queues background tasks for processing
- Returns complex response objects

### Test Objective
Verify that the document upload endpoint correctly:
1. Accepts file uploads and extracts content
2. Detects duplicate documents based on content
3. Generates unique filenames when conflicts exist
4. Returns proper `DocumentUploadResponse` with all fields populated
5. Creates a valid task ID and queues processing

### Test Cases
1. **Successful Upload**: Upload a new document and verify response structure
2. **Duplicate Detection**: Upload the same document twice and verify duplicate status
3. **Filename Conflict Resolution**: Upload files with same name and verify unique naming

### Fields and Return Objects Tested
- `DocumentUploadResponse` object with fields:
  - `filename` (str)
  - `status` (str)
  - `message` (str)
  - `doc_id` (str)
  - `task_id` (str)
  - `timestamp` (datetime)

### Mock Dependencies
- `UploadFile` object
- `DocumentService.check_duplicate()`
- `DatabaseService.insert_document()`
- `TaskManager.add_task()`

---

## Test 2: Category Management API

### Feature Under Test
**API Endpoint**: `PUT /categories/files/{file_id}/category`  
**File**: `category_api.py`  
**Function**: `change_file_category()`

### Code Complexity
- Updates document categorization in database
- Validates file existence before updating
- Handles manual category reassignment
- Updates categorization source metadata
- Returns success/failure status with detailed messages

### Test Objective
Verify that category change endpoint:
1. Successfully updates file category when file exists
2. Returns 404 error when file doesn't exist
3. Properly updates the `cluster_id` field in database
4. Sets `categorization_source` to "manual_edit"
5. Returns correct success response structure

### Test Cases
1. **Valid Category Change**: Change category for existing file
2. **Non-existent File**: Attempt to change category for invalid file ID
3. **Database Update Verification**: Verify cluster_id is updated correctly

### Fields and Return Objects Tested
- Response dictionary with fields:
  - `success` (bool)
  - `message` (str)
- Database fields:
  - `cluster_id` (int)
  - `categorization_source` (str)

### Mock Dependencies
- `DatabaseService.get_document()`
- `DatabaseService.update_document()`
- Form parameters: `category_id`, `category_name`

---

## Test 3: Notifications API

### Feature Under Test
**API Endpoint**: `GET /notifications`  
**File**: `notifications_api.py`  
**Function**: `get_notifications()`

### Code Complexity
- Retrieves notifications from database using stored procedures
- Filters notifications by user ID
- Supports unread-only filtering
- Calculates unread count
- Applies pagination limit
- Parses JSONB notification data
- Returns complex nested response structure

### Test Objective
Verify that notifications endpoint:
1. Retrieves all notifications for a specific user
2. Correctly filters unread notifications when requested
3. Returns accurate unread count
4. Applies limit parameter correctly
5. Properly parses notification metadata
6. Returns `NotificationListResponse` with all nested fields

### Test Cases
1. **All Notifications**: Retrieve all notifications for a user
2. **Unread Only Filter**: Filter to show only unread notifications
3. **Limit Application**: Verify limit parameter restricts results correctly

### Fields and Return Objects Tested
- `NotificationListResponse` object with fields:
  - `notifications` (List[NotificationResponse])
  - `total` (int)
  - `unread_count` (int)
- `NotificationResponse` objects with fields:
  - `id` (str)
  - `document_id` (str)
  - `filename` (str)
  - `title` (str)
  - `message` (str)
  - `type` (str)
  - `metadata` (Dict[str, Any])
  - `is_read` (bool)
  - `created_at` (str)

### Mock Dependencies
- `DatabaseService.client.rpc()` for stored procedures:
  - `get_user_notifications`
  - `get_unread_notification_count`

---

## Testing Framework Setup

### Framework Choice
**pytest** - Python's most popular testing framework

### Installation
```bash
pip install pytest pytest-asyncio pytest-mock httpx
```

### Project Structure
```
tests/
├── __init__.py
├── test_upload_api.py
├── test_category_api.py
├── test_notifications_api.py
└── conftest.py  # Shared fixtures
```

### Required Dependencies
- `pytest`: Core testing framework
- `pytest-asyncio`: For async test support
- `pytest-mock`: For mocking dependencies
- `httpx`: For FastAPI TestClient
- `fastapi.testclient`: For API endpoint testing

---

## Test Execution Strategy

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_upload_api.py -v

# Run with coverage report
pytest tests/ --cov=api --cov-report=html
```

### Expected Output Format
- pytest will generate detailed test results
- HTML coverage report will be generated in `htmlcov/` directory
- JUnit XML report can be generated for CI/CD integration

### Success Criteria
- All 9 test cases pass (3 per test file)
- Code coverage > 80% for tested modules
- No errors or warnings in test execution
- Proper mocking of external dependencies

---

## Deliverables

### 1. Testing Plan (This Document)
- Location in repo: `docs/testing/unit_test_plan.md`
- Committed to: `main` branch

### 2. Test Implementation
- Location in repo: `tests/` directory
- Files: `test_upload_api.py`, `test_category_api.py`, `test_notifications_api.py`

### 3. Test Execution Report
- HTML coverage report: `docs/testing/coverage_report/`
- pytest output: `docs/testing/test_results.html`
- Generated using: `pytest --html=test_results.html --self-contained-html`

---

## Timeline

1. **Testing Plan Creation** (Nov 23): ✓ Complete
2. **Test Implementation** (Nov 24): Write all 9 test cases
3. **Test Execution & Debugging** (Nov 25): Run tests, fix issues
4. **Documentation & Submission** (Nov 26): Generate reports, commit to repo

---

## Notes

- All tests will use mocking to avoid dependencies on external services (database, ML models)
- Tests focus on API layer logic, not integration testing
- Each test verifies both successful and error cases
- Return objects and their fields are thoroughly validated
- Tests are isolated and can run independently

---

## References

- pytest documentation: https://docs.pytest.org/
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
