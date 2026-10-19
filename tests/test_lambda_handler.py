#!/usr/bin/env python3
"""
Tests for Lambda handler with encoding fixes
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLambdaHandler(unittest.TestCase):
    """Test Lambda handler functionality"""

    def setUp(self):
        """Set up test environment"""
        # Import after setting up environment
        import lambda_handler
        self.handler = lambda_handler.handler

    def test_basic_invocation(self):
        """Test basic Lambda invocation"""
        event = {
            'requestContext': {
                'http': {
                    'method': 'GET'
                }
            },
            'rawPath': '/',
            'headers': {}
        }
        context = Mock()

        with patch('lambda_handler.base_handler') as mock_base_handler:
            mock_base_handler.return_value = {
                'statusCode': 200,
                'body': 'OK'
            }

            result = self.handler(event, context)

            self.assertEqual(result['statusCode'], 200)

    def test_hebrew_text_in_headers(self):
        """Test that Hebrew text in headers is properly sanitized"""
        event = {
            'requestContext': {
                'http': {
                    'method': 'POST'
                }
            },
            'rawPath': '/api/upload',
            'headers': {},
            'body': json.dumps({
                'title': 'בכורות דף יט'
            })
        }
        context = Mock()

        with patch('lambda_handler.base_handler') as mock_base_handler:
            # Simulate response with Hebrew in headers (which would cause Latin-1 error)
            mock_base_handler.return_value = {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'X-Custom': 'בכורות'  # Hebrew in header - should be sanitized
                },
                'body': json.dumps({'success': True})
            }

            result = self.handler(event, context)

            # Should succeed and sanitize headers
            self.assertEqual(result['statusCode'], 200)
            # Hebrew characters should be removed or escaped from headers
            self.assertIsInstance(result['headers']['X-Custom'], str)

    def test_unicode_encode_error_handling(self):
        """Test that UnicodeEncodeError is caught and handled"""
        event = {
            'requestContext': {
                'http': {
                    'method': 'POST'
                }
            },
            'rawPath': '/api/upload'
        }
        context = Mock()

        with patch('lambda_handler.base_handler') as mock_base_handler:
            # Simulate UnicodeEncodeError
            mock_base_handler.side_effect = UnicodeEncodeError(
                'latin-1', 'בכורות', 0, 2, 'ordinal not in range(256)'
            )

            result = self.handler(event, context)

            # Should return error response instead of crashing
            self.assertEqual(result['statusCode'], 500)
            body = json.loads(result['body'])
            self.assertFalse(body['success'])
            self.assertIn('encoding', body['error'].lower())

    def test_general_exception_handling(self):
        """Test general exception handling"""
        event = {
            'requestContext': {
                'http': {
                    'method': 'GET'
                }
            },
            'rawPath': '/'
        }
        context = Mock()

        with patch('lambda_handler.base_handler') as mock_base_handler:
            mock_base_handler.side_effect = Exception('Test error')

            result = self.handler(event, context)

            self.assertEqual(result['statusCode'], 500)
            body = json.loads(result['body'])
            self.assertFalse(body['success'])


class TestThumbnailGeneration(unittest.TestCase):
    """Test thumbnail generation with Hebrew text"""

    def setUp(self):
        """Set up test fixtures"""
        import zoom_to_youtube
        self.create_thumbnail = zoom_to_youtube.create_thumbnail

    @patch('zoom_to_youtube.ImageFont.truetype')
    @patch('zoom_to_youtube.Image.open')
    def test_hebrew_text_with_font_failure(self, mock_image_open, mock_truetype):
        """Test thumbnail creation when Hebrew font fails to load"""
        import tempfile
        import os

        # Mock image
        mock_img = MagicMock()
        mock_img.size = (1280, 720)
        mock_image_open.return_value = mock_img

        # Simulate font loading failure
        mock_truetype.side_effect = Exception('Font loading failed')

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
            template_path = tf.name

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
            output_path = tf.name

        try:
            # Should not raise exception, but gracefully handle Hebrew text
            result = self.create_thumbnail(
                'בכורות - יט',
                output_path,
                template_path
            )

            # Should return output path even if text rendering failed
            self.assertIsNotNone(result)

        finally:
            if os.path.exists(template_path):
                os.unlink(template_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch('zoom_to_youtube.ImageFont.load_default')
    @patch('zoom_to_youtube.ImageDraw.Draw')
    @patch('zoom_to_youtube.Image.open')
    def test_unicode_encode_error_in_textbbox(self, mock_image_open, mock_draw, mock_load_default):
        """Test handling of UnicodeEncodeError in textbbox (PIL limitation)"""
        import tempfile
        import os

        # Mock image
        mock_img = MagicMock()
        mock_img.size = (1280, 720)
        mock_image_open.return_value = mock_img

        # Mock draw
        mock_draw_obj = MagicMock()
        # Simulate the Latin-1 encoding error when trying to render Hebrew
        mock_draw_obj.textbbox.side_effect = UnicodeEncodeError(
            'latin-1', 'בכורות', 0, 2, 'ordinal not in range(256)'
        )
        mock_draw.return_value = mock_draw_obj

        # Mock font
        mock_load_default.return_value = MagicMock()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
            template_path = tf.name

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
            output_path = tf.name

        try:
            # Should handle the error gracefully
            result = self.create_thumbnail(
                'בכורות - יט',
                output_path,
                template_path
            )

            # Should still return output path (template saved without text)
            self.assertIsNotNone(result)

        finally:
            if os.path.exists(template_path):
                os.unlink(template_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestRTLTextProcessing(unittest.TestCase):
    """Test Right-to-Left text processing for Hebrew"""

    def test_rtl_support_available(self):
        """Test that RTL support modules are importable"""
        try:
            import arabic_reshaper  # noqa: F401
            from bidi.algorithm import get_display  # noqa: F401
            rtl_available = True
        except ImportError:
            rtl_available = False

        # RTL support should be available for Hebrew text
        self.assertTrue(rtl_available, "RTL support libraries not installed")

    @patch('zoom_to_youtube.Image.open')
    @patch('zoom_to_youtube.RTL_SUPPORT', True)
    def test_hebrew_text_processing(self, mock_image_open):
        """Test that Hebrew text goes through RTL processing"""
        import zoom_to_youtube
        import tempfile

        mock_img = MagicMock()
        mock_img.size = (1280, 720)
        mock_image_open.return_value = mock_img

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
            template_path = tf.name
            output_path = tf.name + '_out.jpg'

        try:
            # This should trigger RTL processing
            with patch('zoom_to_youtube.arabic_reshaper.reshape') as mock_reshape:
                with patch('zoom_to_youtube.get_display') as mock_get_display:
                    mock_reshape.return_value = 'reshaped'
                    mock_get_display.return_value = 'displayed'

                    zoom_to_youtube.create_thumbnail(
                        'בכורות - יט',
                        output_path,
                        template_path
                    )

                    # Verify RTL processing was attempted
                    mock_reshape.assert_called()
                    mock_get_display.assert_called()

        finally:
            import os
            if os.path.exists(template_path):
                os.unlink(template_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == '__main__':
    unittest.main()
