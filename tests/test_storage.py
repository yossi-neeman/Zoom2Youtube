#!/usr/bin/env python3
"""
Unit tests for storage abstraction layer
Tests both local and S3 storage backends
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage import LocalStorage, S3Storage, Storage, get_storage


class TestLocalStorage(unittest.TestCase):
    """Test cases for LocalStorage backend"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.storage = LocalStorage(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_file(self):
        """Test saving a file"""
        # Create a test file
        test_file = os.path.join(self.test_dir, 'source.txt')
        with open(test_file, 'w') as f:
            f.write('test content')

        # Save it to a new location
        result = self.storage.save_file(test_file, 'dest/file.txt')

        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'dest/file.txt')))

    def test_read_file(self):
        """Test reading a file"""
        test_content = b'test binary content'
        test_key = 'test/file.bin'

        # Create test file
        test_path = os.path.join(self.test_dir, test_key)
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, 'wb') as f:
            f.write(test_content)

        # Read it back
        content = self.storage.read_file(test_key)
        self.assertEqual(content, test_content)

    def test_write_text(self):
        """Test writing text"""
        test_text = 'Hello, World!'
        test_key = 'test.txt'

        self.storage.write_text(test_key, test_text)

        # Verify it was written
        self.assertTrue(self.storage.exists(test_key))
        self.assertEqual(self.storage.read_text(test_key), test_text)

    def test_exists(self):
        """Test checking file existence"""
        self.assertFalse(self.storage.exists('nonexistent.txt'))

        # Create a file
        self.storage.write_text('exists.txt', 'content')
        self.assertTrue(self.storage.exists('exists.txt'))

    def test_delete(self):
        """Test deleting a file"""
        self.storage.write_text('to_delete.txt', 'content')
        self.assertTrue(self.storage.exists('to_delete.txt'))

        self.storage.delete('to_delete.txt')
        self.assertFalse(self.storage.exists('to_delete.txt'))

    def test_list_files(self):
        """Test listing files"""
        # Create some files
        self.storage.write_text('dir1/file1.txt', 'content1')
        self.storage.write_text('dir1/file2.txt', 'content2')
        self.storage.write_text('dir2/file3.txt', 'content3')

        # List files in dir1
        files = self.storage.list_files('dir1')
        self.assertEqual(len(files), 2)

    def test_get_local_path(self):
        """Test getting local path"""
        test_key = 'test/file.txt'
        self.storage.write_text(test_key, 'content')

        local_path = self.storage.get_local_path(test_key)
        self.assertTrue(os.path.exists(local_path))
        self.assertIn(test_key, local_path)


class TestS3Storage(unittest.TestCase):
    """Test cases for S3Storage backend"""

    def setUp(self):
        """Set up test fixtures with mocked S3"""
        self.mock_s3_client = MagicMock()
        self.bucket_name = 'test-bucket'
        self.prefix = 'test-prefix'

        with patch('storage.boto3.client', return_value=self.mock_s3_client):
            self.storage = S3Storage(self.bucket_name, self.prefix)

    def test_save_file(self):
        """Test saving a file to S3"""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b'test content')
            temp_path = tf.name

        try:
            result = self.storage.save_file(temp_path, 'test/file.txt')

            self.mock_s3_client.upload_file.assert_called_once()
            self.assertIn('s3://', result)
            self.assertIn(self.bucket_name, result)
        finally:
            os.unlink(temp_path)

    def test_read_file(self):
        """Test reading a file from S3"""
        test_content = b'test content'
        mock_response = {'Body': Mock(read=lambda: test_content)}
        self.mock_s3_client.get_object.return_value = mock_response

        content = self.storage.read_file('test/file.txt')

        self.assertEqual(content, test_content)
        self.mock_s3_client.get_object.assert_called_once()

    def test_exists_true(self):
        """Test checking if file exists in S3 (true case)"""
        self.mock_s3_client.head_object.return_value = {}

        result = self.storage.exists('test/file.txt')

        self.assertTrue(result)
        self.mock_s3_client.head_object.assert_called_once()

    def test_exists_false(self):
        """Test checking if file exists in S3 (false case)"""
        self.mock_s3_client.head_object.side_effect = Exception('Not found')

        result = self.storage.exists('test/file.txt')

        self.assertFalse(result)

    def test_write_text(self):
        """Test writing text to S3"""
        test_text = 'Hello S3!'

        self.storage.write_text('test.txt', test_text)

        self.mock_s3_client.put_object.assert_called_once()
        call_args = self.mock_s3_client.put_object.call_args
        self.assertEqual(call_args[1]['Bucket'], self.bucket_name)
        self.assertEqual(call_args[1]['Body'], test_text.encode('utf-8'))

    def test_delete(self):
        """Test deleting from S3"""
        self.storage.delete('test/file.txt')

        self.mock_s3_client.delete_object.assert_called_once()

    def test_prefix_handling(self):
        """Test that S3 keys are properly prefixed"""
        self.mock_s3_client.head_object.return_value = {}

        self.storage.exists('test.txt')

        call_args = self.mock_s3_client.head_object.call_args
        key = call_args[1]['Key']
        self.assertTrue(key.startswith(self.prefix))


class TestStorageFactory(unittest.TestCase):
    """Test cases for Storage factory"""

    def test_local_storage_by_default(self):
        """Test that local storage is used by default"""
        with patch.dict(os.environ, {'USE_S3_STORAGE': 'false'}, clear=True):
            storage = Storage()
            self.assertTrue(storage.is_local())
            self.assertFalse(storage.is_s3())

    def test_s3_storage_when_enabled(self):
        """Test that S3 storage is used when enabled"""
        with patch.dict(os.environ, {
            'USE_S3_STORAGE': 'true',
            'S3_BUCKET': 'test-bucket',
            'S3_PREFIX': 'test-prefix'
        }, clear=True):
            with patch('storage.boto3.client'):
                storage = Storage()
                self.assertTrue(storage.is_s3())
                self.assertFalse(storage.is_local())

    def test_s3_storage_missing_bucket(self):
        """Test that S3 storage raises error without bucket"""
        with patch.dict(os.environ, {'USE_S3_STORAGE': 'true'}, clear=True):
            with self.assertRaises(ValueError):
                Storage()

    def test_get_storage_singleton(self):
        """Test that get_storage returns singleton"""
        with patch.dict(os.environ, {'USE_S3_STORAGE': 'false'}, clear=True):
            storage1 = get_storage()
            storage2 = get_storage()
            # Should be the same instance
            self.assertIs(storage1, storage2)


if __name__ == '__main__':
    unittest.main()
