# Zoom2Youtube Test Suite

Comprehensive regression tests for the Zoom2Youtube application.

## Test Coverage

### 1. Storage Tests (`test_storage.py`)
- **LocalStorage**: File operations on local filesystem
- **S3Storage**: File operations with AWS S3
- **Storage Factory**: Dynamic backend selection based on environment

### 2. Web Application Tests (`test_web_app.py`)
- **API Endpoints**: All REST endpoints (/api/recordings, /api/download, /api/upload, /api/playlists)
- **Hebrew Text Handling**: UTF-8 encoding in requests and responses
- **S3 Integration**: File persistence across Lambda invocations
- **Error Handling**: Missing parameters, file not found, etc.

### 3. Lambda Handler Tests (`test_lambda_handler.py`)
- **Encoding Fixes**: Hebrew text in headers (Latin-1 constraint)
- **Error Handling**: UnicodeEncodeError, general exceptions
- **Thumbnail Generation**: Hebrew font fallback, encoding errors in PIL

### 4. Zoom Downloader Tests (`test_zoom_downloader.py`)
- OAuth authentication
- Recording retrieval with pagination
- Date range filtering
- File download

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test File
```bash
python -m unittest tests/test_storage.py
python -m unittest tests/test_web_app.py
python -m unittest tests/test_lambda_handler.py
```

### Run Specific Test Class
```bash
python -m unittest tests.test_storage.TestLocalStorage
```

### Run Single Test Method
```bash
python -m unittest tests.test_storage.TestLocalStorage.test_save_file
```

## Test Dependencies

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

## Key Bug Fixes Covered

### 1. Hebrew Text Encoding (Fixed)
- **Problem**: `'latin-1' codec can't encode characters in position 0-1`
- **Fix**: Graceful error handling in thumbnail generation
- **Tests**: `TestHebrewTextHandling`, `TestThumbnailGeneration`

### 2. S3 Persistence Across Lambda Invocations (Fixed)
- **Problem**: Files downloaded in one Lambda invocation weren't available in the next
- **Fix**: Save downloaded files to S3 for persistence
- **Tests**: `TestS3Integration.test_download_persists_to_s3`, `test_upload_retrieves_from_s3`

### 3. Storage Method Name (Fixed)
- **Problem**: `'Storage' object has no attribute 'write_file'`
- **Fix**: Use correct method name `save_file()`
- **Tests**: `TestLocalStorage.test_save_file`, `TestS3Storage.test_save_file`

## Continuous Integration

These tests should be run:
- Before deploying to Lambda
- After any code changes
- As part of CI/CD pipeline

## Test Environment Variables

Tests use local storage by default. To test with S3:
```bash
export USE_S3_STORAGE=true
export S3_BUCKET=your-test-bucket
export S3_PREFIX=test-prefix
```

## Coverage Report

To generate coverage report:
```bash
pip install coverage
coverage run -m unittest discover tests
coverage report
coverage html  # Generates htmlcov/index.html
```

## Writing New Tests

When adding new features, add corresponding tests:

1. **Unit tests**: Test individual functions/methods in isolation
2. **Integration tests**: Test interaction between components
3. **Regression tests**: Test previously fixed bugs don't reoccur

Example:
```python
def test_new_feature(self):
    """Test description"""
    # Arrange
    test_data = {...}
    
    # Act
    result = function_to_test(test_data)
    
    # Assert
    self.assertEqual(result, expected_value)
```

## Mocking External Services

Tests use mocks for external services:
- **Zoom API**: Mocked in `test_zoom_downloader.py`
- **YouTube API**: Mocked in `test_web_app.py`
- **AWS S3**: Mocked in `test_storage.py`

This ensures tests run quickly and don't depend on external services.
