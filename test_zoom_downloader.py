#!/usr/bin/env python3
"""
Unit tests for Zoom Recording Downloader
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from datetime import datetime

# Import the module to test
from zoom_downloader import ZoomRecordingDownloader


class TestZoomRecordingDownloader(unittest.TestCase):
    """Test cases for ZoomRecordingDownloader class"""

    def setUp(self):
        """Set up test fixtures"""
        self.account_id = "test_account_id"
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.downloader = ZoomRecordingDownloader(
            self.account_id,
            self.client_id,
            self.client_secret
        )

    def test_initialization(self):
        """Test that the downloader initializes correctly"""
        self.assertEqual(self.downloader.account_id, self.account_id)
        self.assertEqual(self.downloader.client_id, self.client_id)
        self.assertEqual(self.downloader.client_secret, self.client_secret)
        self.assertIsNone(self.downloader.access_token)
        self.assertEqual(self.downloader.base_url, "https://api.zoom.us/v2")

    @patch('zoom_downloader.requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful OAuth token retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_token_123'}
        mock_post.return_value = mock_response

        token = self.downloader.get_access_token()

        self.assertEqual(token, 'test_token_123')
        self.assertEqual(self.downloader.access_token, 'test_token_123')
        mock_post.assert_called_once()

    @patch('zoom_downloader.requests.post')
    def test_get_access_token_failure(self, mock_post):
        """Test OAuth token retrieval failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.downloader.get_access_token()

        self.assertIn("Failed to get access token", str(context.exception))

    @patch('zoom_downloader.requests.get')
    def test_get_recordings_success(self, mock_get):
        """Test successful recordings retrieval"""
        self.downloader.access_token = 'test_token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'meetings': [
                {
                    'id': '123',
                    'topic': 'Test Meeting',
                    'start_time': '2024-01-15T10:00:00Z',
                    'duration': 60
                }
            ],
            'next_page_token': None
        }
        mock_get.return_value = mock_response

        recordings = self.downloader.get_recordings(user_id='me')

        self.assertEqual(len(recordings), 1)
        self.assertEqual(recordings[0]['topic'], 'Test Meeting')
        self.assertEqual(recordings[0]['id'], '123')

    @patch('zoom_downloader.requests.get')
    def test_get_recordings_pagination(self, mock_get):
        """Test recordings retrieval with pagination"""
        self.downloader.access_token = 'test_token'

        # First page
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            'meetings': [{'id': '1', 'topic': 'Meeting 1'}],
            'next_page_token': 'token_123'
        }

        # Second page
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            'meetings': [{'id': '2', 'topic': 'Meeting 2'}],
            'next_page_token': None
        }

        mock_get.side_effect = [mock_response_1, mock_response_2]

        recordings = self.downloader.get_recordings(user_id='me')

        self.assertEqual(len(recordings), 2)
        self.assertEqual(recordings[0]['id'], '1')
        self.assertEqual(recordings[1]['id'], '2')

    @patch('zoom_downloader.requests.get')
    def test_get_recordings_with_dates(self, mock_get):
        """Test recordings retrieval with date range"""
        self.downloader.access_token = 'test_token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'meetings': [],
            'next_page_token': None
        }
        mock_get.return_value = mock_response

        from_date = '2024-01-01'
        to_date = '2024-01-31'

        self.downloader.get_recordings(
            user_id='me',
            from_date=from_date,
            to_date=to_date
        )

        # Verify the dates were passed correctly
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertEqual(params['from'], from_date)
        self.assertEqual(params['to'], to_date)

    @patch('zoom_downloader.requests.get')
    @patch('zoom_downloader.Path')
    @patch('builtins.open', create=True)
    def test_download_recording_success(self, mock_open, mock_path, mock_get):
        """Test successful recording download"""
        self.downloader.access_token = 'test_token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content = lambda chunk_size: [b'test_data']
        mock_get.return_value = mock_response

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = self.downloader.download_recording(
            'https://zoom.us/rec/download/test.mp4',
            'output',
            'test.mp4'
        )

        self.assertIn('test.mp4', result)
        mock_file.write.assert_called()

    @patch('zoom_downloader.requests.get')
    def test_download_recording_failure(self, mock_get):
        """Test recording download failure"""
        self.downloader.access_token = 'test_token'

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.downloader.download_recording(
                'https://zoom.us/rec/download/test.mp4',
                'output',
                'test.mp4'
            )

        self.assertIn("Failed to download recording", str(context.exception))

    def test_date_defaults(self):
        """Test default date range calculation"""
        with patch('zoom_downloader.requests.get') as mock_get:
            self.downloader.access_token = 'test_token'

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'meetings': [],
                'next_page_token': None
            }
            mock_get.return_value = mock_response

            self.downloader.get_recordings(user_id='me')

            # Verify default date range is 30 days
            call_args = mock_get.call_args
            params = call_args[1]['params']

            from_date = datetime.strptime(params['from'], '%Y-%m-%d')
            to_date = datetime.strptime(params['to'], '%Y-%m-%d')

            # Should be approximately 30 days
            delta = (to_date - from_date).days
            self.assertGreaterEqual(delta, 29)
            self.assertLessEqual(delta, 31)


class TestModuleStructure(unittest.TestCase):
    """Test module structure and imports"""

    def test_module_imports(self):
        """Test that all required modules can be imported"""
        try:
            import os  # noqa: F401
            import requests  # noqa: F401
            from datetime import datetime, timedelta  # noqa: F401
            from pathlib import Path  # noqa: F401
        except ImportError as e:
            self.fail(f"Failed to import required module: {e}")

    def test_class_exists(self):
        """Test that ZoomRecordingDownloader class exists"""
        self.assertTrue(hasattr(ZoomRecordingDownloader, '__init__'))
        self.assertTrue(hasattr(ZoomRecordingDownloader, 'get_access_token'))
        self.assertTrue(hasattr(ZoomRecordingDownloader, 'get_recordings'))
        self.assertTrue(hasattr(ZoomRecordingDownloader, 'download_recording'))
        self.assertTrue(hasattr(ZoomRecordingDownloader, 'download_all_recordings'))


def run_tests():
    """Run all tests and return results"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    print("Running Zoom Recording Downloader Tests...\n")
    result = run_tests()

    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
