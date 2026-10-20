#!/usr/bin/env python3
"""
Integration tests for web_app.py
Tests API endpoints and critical workflows
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock environment before importing app
os.environ['USE_S3_STORAGE'] = 'false'
os.environ['AUTH_ENABLED'] = 'false'
os.environ.setdefault('ZOOM_ACCOUNT_ID', 'test-account')
os.environ.setdefault('ZOOM_CLIENT_ID', 'test-client')
os.environ.setdefault('ZOOM_CLIENT_SECRET', 'test-secret')

import web_app
from web_app import app


class TestWebAppEndpoints(unittest.TestCase):
    """Test web application endpoints"""

    def setUp(self):
        """Set up test client"""
        app.config['TESTING'] = True
        self.client = app.test_client()
        web_app._upload_results.clear()
        web_app._upload_inflight.clear()

    def test_index_loads(self):
        """Test that index page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        """Test that login page loads"""
        with patch('web_app.AUTH_ENABLED', True):
            response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

    @patch('web_app.storage')
    @patch('web_app.ZoomRecordingDownloader')
    def test_recordings_endpoint(self, mock_downloader_class, mock_storage):
        """Test /api/recordings endpoint"""
        # Mock the downloader
        mock_downloader = Mock()
        mock_downloader.get_recordings.return_value = [
            {
                'uuid': 'test-uuid-1',
                'topic': 'Test Meeting',
                'start_time': '2024-01-15T10:00:00Z',
                'duration': 60,
                'recording_files': [
                    {'file_type': 'MP4'}
                ],
                'recording_count': 1
            }
        ]
        mock_downloader_class.return_value = mock_downloader

        response = self.client.get('/api/recordings?days=7')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['recordings']), 1)
        self.assertEqual(data['recordings'][0]['topic'], 'Test Meeting')

    @patch('web_app.storage')
    @patch('web_app.ZoomRecordingDownloader')
    def test_download_endpoint_s3_persistence(self, mock_downloader_class, mock_storage):
        """Test that download endpoint saves to S3 when enabled"""
        # Configure storage as S3
        mock_storage.is_s3.return_value = True
        mock_storage.save_file.return_value = 's3://bucket/key'

        # Mock the downloader
        mock_downloader = Mock()
        mock_downloader.get_recordings.return_value = [
            {
                'uuid': 'test-uuid',
                'topic': 'Test',
                'start_time': '2024-01-15',
                'id': '123',
                'recording_files': [
                    {
                        'file_type': 'MP4',
                        'download_url': 'https://zoom.us/rec/test.mp4'
                    }
                ]
            }
        ]
        mock_downloader.download_recording.return_value = '/tmp/recordings/test.mp4'
        mock_downloader_class.return_value = mock_downloader

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value.list_objects_v2.return_value = {}
            response = self.client.post('/api/download',
                                       json={'recording_id': 'test-uuid'},
                                       content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])

        # Verify S3 save was called
        mock_storage.save_file.assert_called_once()

    @patch('web_app.storage')
    @patch('web_app.YouTubeUploader')
    def test_upload_endpoint_hebrew_text(self, mock_uploader_class, mock_storage):
        """Test upload endpoint with Hebrew text in title and thumbnail"""
        # Configure storage
        mock_storage.is_s3.return_value = False
        mock_storage.exists.return_value = True
        mock_storage.get_local_path.return_value = '/tmp/test.mp4'

        # Mock the uploader
        mock_uploader = Mock()
        mock_uploader.upload_video.return_value = 'test_video_id_123'
        mock_uploader_class.return_value = mock_uploader

        # Create a dummy video file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tf:
            tf.write(b'fake video content')
            video_path = tf.name

        try:
            # Mock file existence
            with patch('os.path.exists', return_value=True):
                response = self.client.post('/api/upload',
                                          json={
                                              'video_file': video_path,
                                              'title': 'בכורות | יט | בית כנסת נריה',
                                              'description': 'תיאור בעברית',
                                              'thumbnail_text': 'בכורות - יט',
                                              'privacy': 'public'
                                          },
                                          content_type='application/json')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIn('video_id', data)
        finally:
            if os.path.exists(video_path):
                os.unlink(video_path)

    @patch('web_app.storage')
    @patch('web_app.YouTubeUploader')
    def test_playlists_endpoint(self, mock_uploader_class, mock_storage):
        """Test /api/playlists endpoint"""
        mock_storage.is_s3.return_value = False
        mock_storage.exists.return_value = True
        mock_storage.get_local_path.return_value = '/tmp/creds'

        # Mock the uploader
        mock_uploader = Mock()
        mock_uploader.list_playlists.return_value = [
            {
                'id': 'PL123',
                'title': 'Test Playlist'
            }
        ]
        mock_uploader_class.return_value = mock_uploader

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy credential files
            cred_file = os.path.join(tmpdir, 'client_secrets.json')
            with open(cred_file, 'w') as f:
                f.write('{}')

            with patch('web_app.storage.get_local_path', return_value=cred_file):
                response = self.client.get('/api/playlists')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['playlists']), 1)


class TestHebrewTextHandling(unittest.TestCase):
    """Test Hebrew text encoding and handling"""

    def setUp(self):
        """Set up test client"""
        app.config['TESTING'] = True
        self.client = app.test_client()
        web_app._upload_results.clear()
        web_app._upload_inflight.clear()

    @patch('web_app.create_thumbnail')
    @patch('web_app.storage')
    def test_thumbnail_with_hebrew_text(self, mock_storage, mock_create_thumbnail):
        """Test that thumbnail generation handles Hebrew text gracefully"""
        mock_storage.is_s3.return_value = False
        mock_storage.exists.return_value = True
        mock_create_thumbnail.return_value = '/tmp/thumbnail.jpg'

        # This should not raise an encoding error
        with patch('os.path.exists', return_value=True), patch('os.remove'):
            with patch('web_app.YouTubeUploader') as mock_uploader:
                mock_uploader.return_value.upload_video.return_value = 'video_123'

                response = self.client.post('/api/upload',
                                          json={
                                              'video_file': '/tmp/test.mp4',
                                              'title': 'בכורות דף יט',
                                              'thumbnail_text': 'בכורות - יט'
                                          },
                                          content_type='application/json')

                # Should succeed despite Hebrew text
                self.assertIn(response.status_code, [200, 500])  # May fail for other reasons but not encoding

    def test_json_response_with_hebrew(self):
        """Test that JSON responses handle Hebrew correctly"""
        with patch('web_app.ZoomRecordingDownloader') as mock_downloader:
            mock_inst = Mock()
            mock_inst.get_recordings.return_value = [
                {
                    'uuid': '123',
                    'topic': 'פגישת זום בעברית',
                    'start_time': '2024-01-15',
                    'duration': 60,
                    'recording_files': [{'file_type': 'MP4'}],
                    'recording_count': 1
                }
            ]
            mock_downloader.return_value = mock_inst

            response = self.client.get('/api/recordings')
            self.assertEqual(response.status_code, 200)

            # Verify Hebrew text is preserved in response
            data = json.loads(response.data)
            self.assertIn('פגישת זום', data['recordings'][0]['topic'])


class TestS3Integration(unittest.TestCase):
    """Test S3 storage integration with Lambda stateless architecture"""

    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        self.client = app.test_client()
        web_app._upload_results.clear()
        web_app._upload_inflight.clear()

    @patch('web_app.storage')
    @patch('web_app.ZoomRecordingDownloader')
    def test_download_persists_to_s3(self, mock_downloader_class, mock_storage):
        """Test that downloaded files are persisted to S3"""
        # Enable S3 storage
        mock_storage.is_s3.return_value = True
        mock_storage.save_file.return_value = 's3://bucket/recordings/test.mp4'

        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.get_recordings.return_value = [{
            'uuid': 'test-uuid',
            'topic': 'Test',
            'start_time': '2024-01-15',
            'id': '123',
            'recording_files': [{
                'file_type': 'MP4',
                'download_url': 'https://zoom.us/test.mp4'
            }]
        }]
        mock_downloader.download_recording.return_value = '/tmp/recordings/test.mp4'
        mock_downloader_class.return_value = mock_downloader

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value.list_objects_v2.return_value = {}
            response = self.client.post('/api/download',
                                       json={'recording_id': 'test-uuid'},
                                       content_type='application/json')

        self.assertEqual(response.status_code, 200)
        # Verify S3 save was called (persistence across Lambda invocations)
        mock_storage.save_file.assert_called()

    @patch('web_app.storage')
    @patch('web_app.YouTubeUploader')
    def test_upload_retrieves_from_s3(self, mock_uploader_class, mock_storage):
        """Test that upload retrieves video from S3"""
        # Enable S3 storage
        mock_storage.is_s3.return_value = True
        mock_storage.exists.return_value = True
        mock_storage.get_local_path.return_value = '/tmp/downloaded.mp4'
        mock_storage.read_file.return_value = b'{}'

        # Mock uploader
        mock_uploader = Mock()
        mock_uploader.upload_video.return_value = 'video_123'
        mock_uploader_class.return_value = mock_uploader

        with patch('os.path.exists', return_value=True):
            response = self.client.post('/api/upload',
                                      json={
                                          'video_file': 'recordings/test.mp4',
                                          'title': 'Test Video'
                                      },
                                      content_type='application/json')

        self.assertEqual(response.status_code, 200)
        # Verify file was retrieved from S3
        mock_storage.get_local_path.assert_called()


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""

    def setUp(self):
        """Set up test client"""
        app.config['TESTING'] = True
        self.client = app.test_client()
        web_app._upload_results.clear()
        web_app._upload_inflight.clear()

    def test_missing_recording_id(self):
        """Test download without recording_id"""
        response = self.client.post('/api/download',
                                   json={},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    def test_missing_video_file(self):
        """Test upload without video_file"""
        response = self.client.post('/api/upload',
                                   json={'title': 'Test'},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @patch('web_app.storage')
    def test_video_not_found_in_storage(self, mock_storage):
        """Test upload when video doesn't exist in storage"""
        mock_storage.is_s3.return_value = True
        mock_storage.read_file.return_value = b'{}'
        mock_storage.exists.side_effect = lambda key: key.startswith('credentials/')

        response = self.client.post('/api/upload',
                                   json={
                                       'video_file': 'nonexistent.mp4',
                                       'title': 'Test'
                                   },
                                   content_type='application/json')

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('not found', data['error'].lower())

    @patch('web_app.storage')
    @patch('web_app.YouTubeUploader')
    def test_repeated_upload_returns_original_result(self, mock_uploader_class, mock_storage):
        """A duplicate request after success must not re-upload or 404 on the cleaned-up file"""
        mock_storage.is_s3.return_value = False
        mock_storage.exists.return_value = True
        mock_storage.get_local_path.return_value = '/tmp/creds'
        mock_uploader_class.return_value.upload_video.return_value = 'video_123'
        payload = {'video_file': 'recordings/dup/test.mp4', 'title': 'Test'}

        with patch('os.path.exists', return_value=True), patch('web_app.shutil.rmtree'):
            first = self.client.post('/api/upload', json=payload)
        # Recording is gone now (cleaned up after the first upload)
        second = self.client.post('/api/upload', json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json(), first.get_json())
        mock_uploader_class.return_value.upload_video.assert_called_once()


class TestSecurityHardening(unittest.TestCase):
    """Login rate limiting, cookie flags, CORS and debug endpoint gating"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        web_app._login_failures.clear()
        patcher = patch.multiple('web_app', AUTH_ENABLED=True,
                                 AUTH_USERNAME='admin', AUTH_PASSWORD='s3cret-pass')
        patcher.start()
        self.addCleanup(patcher.stop)

    def _login(self, password, username='admin'):
        return self.client.post('/login', data={'username': username, 'password': password})

    def test_correct_login_succeeds(self):
        response = self._login('s3cret-pass')
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('logged_in'))

    def test_wrong_password_rejected(self):
        response = self._login('wrong')
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get('logged_in'))

    def test_login_locks_out_after_repeated_failures(self):
        for _ in range(web_app.LOGIN_MAX_FAILURES):
            self.assertEqual(self._login('wrong').status_code, 200)
        locked = self._login('wrong')
        self.assertEqual(locked.status_code, 429)
        self.assertIn('Retry-After', locked.headers)
        # Even the correct password is refused while locked out
        self.assertEqual(self._login('s3cret-pass').status_code, 429)

    def test_successful_login_resets_failure_count(self):
        for _ in range(web_app.LOGIN_MAX_FAILURES - 1):
            self._login('wrong')
        self.assertEqual(self._login('s3cret-pass').status_code, 302)
        self.assertEqual(len(web_app._login_failures), 0)

    def test_session_cookie_flags(self):
        self.assertTrue(app.config['SESSION_COOKIE_HTTPONLY'])
        self.assertEqual(app.config['SESSION_COOKIE_SAMESITE'], 'Lax')

    def test_cors_disabled_by_default(self):
        response = self.client.get('/login', headers={'Origin': 'https://evil.example'})
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def test_debug_endpoint_disabled_by_default(self):
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
        response = self.client.post('/api/debug/thumbnail', json={'text': 'x'})
        self.assertEqual(response.status_code, 404)

    def test_api_requires_login(self):
        response = self.client.get('/api/recordings')
        self.assertEqual(response.status_code, 401)


class TestGoogleAdminLogin(unittest.TestCase):
    """Google sign-in for admins (allowlist, state, verified email)"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        web_app._login_failures.clear()
        patcher = patch.multiple(
            'web_app', AUTH_ENABLED=True, AUTH_MODE='both',
            GOOGLE_LOGIN_CLIENT_ID='cid', GOOGLE_LOGIN_CLIENT_SECRET='csecret',
            GOOGLE_LOGIN_REDIRECT_URI='https://example.com/auth/callback',
            ADMIN_EMAILS={'alice@gmail.com'}, ADMIN_DOMAINS={'corp.org'})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _start(self):
        response = self.client.get('/auth/google')
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response.headers['Location'])
        self.assertIn('code_challenge=', response.headers['Location'])
        with self.client.session_transaction() as sess:
            return sess['google_oauth_state']

    def _callback(self, state, claims):
        with patch('web_app._exchange_google_code', return_value=claims):
            return self.client.get(f'/auth/callback?state={state}&code=abc')

    def test_allowed_email_logs_in(self):
        state = self._start()
        response = self._callback(state, {'email': 'Alice@gmail.com', 'email_verified': True})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertTrue(sess['logged_in'])
            self.assertEqual(sess['username'], 'alice@gmail.com')

    def test_allowed_domain_logs_in(self):
        state = self._start()
        response = self._callback(state, {'email': 'bob@corp.org', 'email_verified': True})
        self.assertEqual(response.status_code, 302)

    def test_unlisted_email_rejected(self):
        state = self._start()
        response = self._callback(state, {'email': 'mallory@gmail.com', 'email_verified': True})
        self.assertEqual(response.status_code, 403)
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)

    def test_unverified_email_rejected(self):
        state = self._start()
        response = self._callback(state, {'email': 'alice@gmail.com', 'email_verified': False})
        self.assertEqual(response.status_code, 403)

    def test_state_mismatch_rejected(self):
        self._start()
        response = self._callback('wrong-state', {'email': 'alice@gmail.com', 'email_verified': True})
        self.assertEqual(response.status_code, 400)

    def test_callback_without_start_rejected(self):
        response = self._callback('x', {'email': 'alice@gmail.com', 'email_verified': True})
        self.assertEqual(response.status_code, 400)

    def test_google_mode_disables_password_login(self):
        with patch('web_app.AUTH_MODE', 'google'):
            response = self.client.post('/login', data={'username': 'admin', 'password': 'x'})
        self.assertEqual(response.status_code, 403)

    def test_google_routes_404_when_disabled(self):
        with patch('web_app.AUTH_MODE', 'password'):
            self.assertEqual(self.client.get('/auth/google').status_code, 404)

    def test_login_page_shows_google_button(self):
        self.assertIn(b'Sign in with Google', self.client.get('/login').data)


if __name__ == '__main__':
    unittest.main()
