#!/usr/bin/env python3
"""
Zoom to YouTube Web Application
"""

import os
import json
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename

from zoom_downloader import ZoomRecordingDownloader
from youtube_uploader import YouTubeUploader
from zoom_to_youtube import create_thumbnail
from version import get_full_version, VERSION
from storage import get_storage

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['JSON_AS_ASCII'] = False  # Allow Unicode characters in JSON responses
CORS(app)

# Middleware to ensure UTF-8 encoding
@app.after_request
def after_request(response):
    # Ensure all responses declare UTF-8 charset
    content_type = response.headers.get('Content-Type', '')
    if content_type and 'charset' not in content_type:
        response.headers['Content-Type'] = content_type + '; charset=utf-8'
    
    # Force response data to be UTF-8 encoded bytes
    if hasattr(response, 'data'):
        if isinstance(response.data, str):
            response.data = response.data.encode('utf-8')
    
    # Ensure all header values are ASCII-safe (escape non-ASCII)
    safe_headers = {}
    for key, value in response.headers:
        if isinstance(value, str):
            try:
                # Try encoding as ASCII to test
                value.encode('ascii')
                safe_headers[key] = value
            except UnicodeEncodeError:
                # If value contains non-ASCII, encode as UTF-8 and represent as ASCII-safe
                safe_headers[key] = value.encode('utf-8').decode('ascii', errors='ignore')
        else:
            safe_headers[key] = value
    
    # Update headers
    for key, value in safe_headers.items():
        response.headers[key] = value
    
    return response

# Initialize storage
storage = get_storage()

# Authentication configuration
AUTH_USERNAME = os.environ.get('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD', 'changeme')
AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'true').lower() == 'true'


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        
        if 'logged_in' not in session or not session['logged_in']:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Configuration
# In Lambda, use /tmp for writable storage
is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
UPLOAD_FOLDER = '/tmp/recordings' if is_lambda else 'recordings'
CREDENTIALS_FOLDER = '/tmp/credentials' if is_lambda else 'credentials'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB max

# Ensure directories exist (only for local storage)
if storage.is_local():
    Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
    Path(CREDENTIALS_FOLDER).mkdir(exist_ok=True)
    Path('static').mkdir(exist_ok=True)
    Path('templates').mkdir(exist_ok=True)
    print(f"💾 Local directories created: {UPLOAD_FOLDER}, {CREDENTIALS_FOLDER}")
else:
    # For S3 storage, still create /tmp directories for temporary file operations
    Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
    print(f"🪣 Using S3 storage - created temp directory: {UPLOAD_FOLDER}")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if not AUTH_ENABLED:
        session['logged_in'] = True
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == AUTH_USERNAME and password == AUTH_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password', version=get_full_version())
    
    # If already logged in, redirect to index
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    return render_template('login.html', version=get_full_version())


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Main dashboard"""
    username = session.get('username', 'User')
    return render_template('index.html', version=get_full_version(), username=username)


@app.route('/api/recordings', methods=['GET'])
@login_required
def get_recordings():
    """Get available Zoom recordings"""
    try:
        days = int(request.args.get('days', 5))
        
        # Get Zoom credentials from environment
        account_id = os.environ.get('ZOOM_ACCOUNT_ID')
        client_id = os.environ.get('ZOOM_CLIENT_ID')
        client_secret = os.environ.get('ZOOM_CLIENT_SECRET')
        
        if not all([account_id, client_id, client_secret]):
            return jsonify({
                'success': False,
                'error': 'Zoom credentials not configured. Please check your .env file.'
            }), 500
        
        zoom_downloader = ZoomRecordingDownloader(account_id, client_id, client_secret)
        
        # Get today's date and date range
        today = datetime.now()
        from_date = (today - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')
        
        recordings = zoom_downloader.get_recordings(
            user_id='me',
            from_date=from_date,
            to_date=to_date
        )
        
        # Filter for MP4 files
        recordings_with_mp4 = []
        for meeting in recordings:
            recording_files = meeting.get('recording_files', [])
            has_mp4 = any(f.get('file_type') == 'MP4' for f in recording_files)
            if has_mp4:
                recordings_with_mp4.append({
                    'id': meeting.get('uuid'),
                    'topic': meeting.get('topic'),
                    'start_time': meeting.get('start_time'),
                    'duration': meeting.get('duration'),
                    'recording_count': meeting.get('recording_count')
                })
        
        return jsonify({
            'success': True,
            'recordings': recordings_with_mp4
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download', methods=['POST'])
@login_required
def download_recording():
    """Download a specific Zoom recording"""
    try:
        data = request.json
        recording_id = data.get('recording_id')
        
        if not recording_id:
            return jsonify({'success': False, 'error': 'Recording ID required'}), 400
        
        # Get Zoom credentials from environment
        account_id = os.environ.get('ZOOM_ACCOUNT_ID')
        client_id = os.environ.get('ZOOM_CLIENT_ID')
        client_secret = os.environ.get('ZOOM_CLIENT_SECRET')
        
        if not all([account_id, client_id, client_secret]):
            return jsonify({
                'success': False,
                'error': 'Zoom credentials not configured'
            }), 500
        
        zoom_downloader = ZoomRecordingDownloader(account_id, client_id, client_secret)
        
        # Get recordings to find the one with matching UUID
        today = datetime.now()
        from_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')
        
        recordings = zoom_downloader.get_recordings(
            user_id='me',
            from_date=from_date,
            to_date=to_date
        )
        
        # Find the recording with matching UUID
        target_recording = None
        for meeting in recordings:
            if meeting.get('uuid') == recording_id:
                target_recording = meeting
                break
        
        if not target_recording:
            return jsonify({
                'success': False,
                'error': 'Recording not found'
            }), 404
        
        # Find the MP4 file in the recording
        recording_files = target_recording.get('recording_files', [])
        mp4_file = None
        for f in recording_files:
            if f.get('file_type') == 'MP4':
                mp4_file = f
                break
        
        if not mp4_file:
            return jsonify({
                'success': False,
                'error': 'No MP4 file found in this recording'
            }), 404
        
        # Prepare file paths
        download_url = mp4_file.get('download_url')
        topic = target_recording.get('topic', 'recording')
        start_time = target_recording.get('start_time', '')
        
        # Create a safe folder name
        folder_name = f"{start_time[:10]}_{topic}_{target_recording.get('id')}"
        safe_folder = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).strip()
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_folder)
        
        # Check if file already exists
        existing_files = []
        
        if storage.is_s3():
            # For S3, check if files exist in S3 storage
            s3_prefix = output_path.replace('/tmp/', '')  # Remove /tmp/ prefix
            # List files in S3 with this prefix
            try:
                import boto3
                s3_client = boto3.client('s3')
                bucket = storage.backend.bucket
                prefix = storage.backend.base_path + '/' + s3_prefix if storage.backend.base_path else s3_prefix
                
                response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        if key.lower().endswith('.mp4'):
                            existing_files.append(key)
            except Exception as e:
                print(f"Error checking S3 for existing files: {e}")
        else:
            # For local storage, check local filesystem
            if os.path.exists(output_path):
                for file in os.listdir(output_path):
                    if file.endswith('.MP4') or file.endswith('.mp4'):
                        existing_files.append(os.path.join(output_path, file))
        
        if existing_files:
            # File already downloaded, return existing path
            filepath = existing_files[0]
            return jsonify({
                'success': True,
                'message': 'Recording already downloaded (using existing file)',
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'already_exists': True
            })
        
        # Download the file
        filepath = zoom_downloader.download_recording(
            download_url=download_url,
            output_path=output_path
        )
        
        # If using S3 storage, upload the file to S3
        if storage.is_s3():
            # Upload the downloaded file to S3
            s3_key = filepath.replace('/tmp/', '')  # Remove /tmp/ prefix for S3 key
            s3_path = storage.save_file(filepath, s3_key)
            print(f"✓ Uploaded to S3: {s3_path}")
            # Return the S3 key as filepath for later retrieval
            filepath = s3_key
        
        return jsonify({
            'success': True,
            'message': 'Recording downloaded successfully',
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'already_exists': False
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/playlists', methods=['GET'])
@login_required
def get_playlists():
    """Get YouTube playlists"""
    try:
        # Get credentials path (download from S3 if needed)
        client_secrets_key = 'credentials/client_secrets.json'
        token_key = 'credentials/youtube_token.pickle'
        
        if not storage.exists(client_secrets_key):
            return jsonify({
                'success': False,
                'error': 'YouTube credentials not found. Please add client_secrets.json to credentials folder.'
            }), 500
        
        # For S3 storage, download both files to a temp directory
        if storage.is_s3():
            import tempfile
            temp_dir = tempfile.mkdtemp()
            
            # Download client_secrets.json
            client_secrets_data = storage.read_file(client_secrets_key)
            client_secrets_path = os.path.join(temp_dir, 'client_secrets.json')
            with open(client_secrets_path, 'wb') as f:
                f.write(client_secrets_data)
            
            # Download youtube_token.pickle if it exists
            if storage.exists(token_key):
                token_data = storage.read_file(token_key)
                token_path = os.path.join(temp_dir, 'youtube_token.pickle')
                with open(token_path, 'wb') as f:
                    f.write(token_data)
        else:
            # For local storage, use direct path
            client_secrets_path = storage.get_local_path(client_secrets_key)
        
        youtube_uploader = YouTubeUploader(client_secrets_file=client_secrets_path)
        playlists = youtube_uploader.list_playlists()
        
        # list_playlists() already returns simplified dictionaries with 'id', 'title', 'item_count'
        return jsonify({
            'success': True,
            'playlists': playlists
        })
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error fetching playlists: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Idempotency for /api/upload: a retried/duplicate request for the same file
# must not re-upload, nor fail with "file not found" once the first one cleaned up.
_upload_lock = threading.Lock()
_upload_results = {}   # video_file -> successful response payload
_upload_inflight = {}  # video_file -> threading.Event set when the upload finishes


@app.route('/api/upload', methods=['POST'])
@login_required
def upload_to_youtube():
    """Upload video to YouTube (idempotent per video_file)"""
    video_file = (request.get_json(force=True, silent=True) or {}).get('video_file', '')
    event = None
    if video_file:
        with _upload_lock:
            if video_file in _upload_results:
                return jsonify(_upload_results[video_file])
            waiting_on = _upload_inflight.get(video_file)
            if waiting_on is None:
                event = _upload_inflight[video_file] = threading.Event()
        if waiting_on is not None:
            waiting_on.wait(timeout=3600)
            with _upload_lock:
                if video_file in _upload_results:
                    return jsonify(_upload_results[video_file])
            return jsonify({'success': False, 'error': 'The previous upload attempt for this recording failed.'}), 500
    try:
        response = _do_upload_to_youtube()
        resp = response[0] if isinstance(response, tuple) else response
        if resp.status_code == 200 and resp.get_json().get('success'):
            with _upload_lock:
                _upload_results[video_file] = resp.get_json()
        return response
    finally:
        if event is not None:
            with _upload_lock:
                _upload_inflight.pop(video_file, None)
            event.set()


def _do_upload_to_youtube():
    try:
        # Get JSON data with explicit UTF-8 handling
        data = request.get_json(force=True)
        
        # Ensure all text fields are properly decoded as UTF-8
        video_file = data.get('video_file', '')
        title = data.get('title', '')
        description = data.get('description', '')
        playlist_id = data.get('playlist_id', '')
        thumbnail_text = data.get('thumbnail_text', '')
        privacy = data.get('privacy', 'private')
        
        # Log what we received (for debugging)
        print(f"Upload request - Title: {repr(title)}, Thumbnail: {repr(thumbnail_text)}")
        
        if not video_file or not title:
            return jsonify({
                'success': False,
                'error': 'Video file and title required'
            }), 400
        
        # Generate thumbnail if text provided
        thumbnail_file = None
        if thumbnail_text:
            thumbnail_file = f'/tmp/temp_thumbnail_{datetime.now().timestamp()}.jpg'
            create_thumbnail(
                thumbnail_text,
                thumbnail_file,
                'graphics_template.jpg'
            )
        
        # Get credentials path (download from S3 if needed)
        client_secrets_key = 'credentials/client_secrets.json'
        token_key = 'credentials/youtube_token.pickle'
        
        if not storage.exists(client_secrets_key):
            return jsonify({
                'success': False,
                'error': 'YouTube credentials not found'
            }), 500
        
        # For S3 storage, download both credential files to a temp directory
        if storage.is_s3():
            import tempfile
            temp_dir = tempfile.mkdtemp()
            
            # Download client_secrets.json
            client_secrets_data = storage.read_file(client_secrets_key)
            client_secrets_path = os.path.join(temp_dir, 'client_secrets.json')
            with open(client_secrets_path, 'wb') as f:
                f.write(client_secrets_data)
            
            # Download youtube_token.pickle if it exists
            if storage.exists(token_key):
                token_data = storage.read_file(token_key)
                token_path = os.path.join(temp_dir, 'youtube_token.pickle')
                with open(token_path, 'wb') as f:
                    f.write(token_data)
        else:
            # For local storage, use direct path
            client_secrets_path = storage.get_local_path(client_secrets_key)
        
        # Check if video file exists
        # For local: video_file is a local path
        # For S3: video_file is the S3 key
        local_video_path = video_file
        if storage.is_s3():
            # For S3 storage, the video_file is the S3 key
            # Check if exists in storage
            print(f"Checking S3 for file: {video_file}")
            if not storage.exists(video_file):
                return jsonify({
                    'success': False,
                    'error': f'Video file not found in storage. Please download the recording again.'
                }), 404
            # Download from S3 to local /tmp for processing
            local_video_path = storage.get_local_path(video_file)
            print(f"Downloaded from S3 to: {local_video_path}")
        else:
            # Local storage - check if file exists
            if not os.path.exists(video_file):
                return jsonify({
                    'success': False,
                    'error': f'Video file not found: {video_file}. Please download the recording again.'
                }), 404
        
        print(f"Uploading video file: {local_video_path}")
        
        # client_secrets_path is already set up above with both credential files
        youtube_uploader = YouTubeUploader(client_secrets_file=client_secrets_path)
        video_id = youtube_uploader.upload_video(
            video_file=local_video_path,
            title=title,
            description=description,
            privacy=privacy,
            playlist_id=playlist_id,
            thumbnail_file=thumbnail_file
        )
        
        # Cleanup thumbnail
        if thumbnail_file and os.path.exists(thumbnail_file):
            os.remove(thumbnail_file)
        
        # Cleanup video file and directory after successful upload
        try:
            if storage.is_s3():
                # For S3: Delete the file/directory from S3
                # Extract the directory prefix from video_file path
                video_key = video_file.replace(app.config['UPLOAD_FOLDER'] + '/', '')
                video_dir = os.path.dirname(video_key)
                
                if video_dir:
                    storage.delete_directory(f"{app.config['UPLOAD_FOLDER']}/{video_dir}")
                    print(f"✓ Cleaned up S3 directory: {video_dir}")
                else:
                    storage.delete(f"{app.config['UPLOAD_FOLDER']}/{video_key}")
                    print(f"✓ Cleaned up S3 file: {video_key}")
                
                # Also cleanup local temp file
                if os.path.exists(local_video_path):
                    os.remove(local_video_path)
            else:
                # For local storage: Remove directory as before
                video_dir = os.path.dirname(video_file)
                
                if video_dir and os.path.exists(video_dir) and video_dir.startswith(app.config['UPLOAD_FOLDER']):
                    shutil.rmtree(video_dir)
                    print(f"✓ Cleaned up recording directory: {video_dir}")
                else:
                    if os.path.exists(video_file):
                        os.remove(video_file)
                        print(f"✓ Cleaned up video file: {video_file}")
        except Exception as cleanup_error:
            print(f"Warning: Could not cleanup video file: {cleanup_error}")
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_url': f'https://www.youtube.com/watch?v={video_id}',
            'cleanup': 'Video file deleted from storage'
        })
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"❌ Upload error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Ensure error message is ASCII-safe for response
        try:
            error_msg.encode('ascii')
        except UnicodeEncodeError:
            # If error contains non-ASCII, sanitize it
            error_msg = error_msg.encode('ascii', errors='replace').decode('ascii')
            print(f"Sanitized error message: {error_msg}")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/thumbnail/preview', methods=['POST'])
@login_required
def preview_thumbnail():
    """Generate thumbnail preview"""
    import sys
    from io import StringIO
    import base64
    
    # Capture stdout to return debug info
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            sys.stdout = old_stdout
            return jsonify({'success': False, 'error': 'Text required'}), 400
        
        # Generate preview in /tmp (Lambda-safe)
        preview_file = f'/tmp/preview_{datetime.now().timestamp()}.jpg'
        create_thumbnail(text, preview_file, 'graphics_template.jpg')
        
        # Read the image and encode as base64 to return directly
        with open(preview_file, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Get captured output
        debug_logs = captured_output.getvalue()
        sys.stdout = old_stdout
        
        # Clean up temp file
        try:
            os.remove(preview_file)
        except:
            pass
        
        return jsonify({
            'success': True,
            'preview_data': f'data:image/jpeg;base64,{img_data}',
            'debug_logs': debug_logs
        })
    
    except Exception as e:
        sys.stdout = old_stdout
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/debug/thumbnail', methods=['POST'])
@login_required
def debug_thumbnail():
    """Generate test thumbnail for debugging"""
    import sys
    from io import StringIO
    import base64
    
    # Capture stdout to return debug info
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        data = request.json
        text = data.get('text', '')
        font_size = data.get('font_size', 200)
        
        if not text:
            sys.stdout = old_stdout
            return jsonify({'success': False, 'error': 'Text required'}), 400
        
        # Generate debug thumbnail in /tmp (Lambda-safe)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_file = f'/tmp/debug_thumbnail_{timestamp}.jpg'
        
        # Import and modify create_thumbnail temporarily
        from zoom_to_youtube import create_thumbnail_with_size
        create_thumbnail_with_size(text, debug_file, 'graphics_template.jpg', font_size)
        
        # Read the image and encode as base64 to return directly
        with open(debug_file, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Get captured output
        debug_logs = captured_output.getvalue()
        sys.stdout = old_stdout
        
        # Clean up temp file
        try:
            os.remove(debug_file)
        except:
            pass
        
        return jsonify({
            'success': True,
            'thumbnail_data': f'data:image/jpeg;base64,{img_data}',
            'font_size': font_size,
            'debug_logs': debug_logs
        })
    
    except Exception as e:
        sys.stdout = old_stdout
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/config', methods=['GET', 'POST'])
@login_required
def config():
    """Get or update configuration"""
    config_key = 'credentials/web_config.json'
    
    if request.method == 'GET':
        if storage.exists(config_key):
            config_data = json.loads(storage.read_text(config_key))
        else:
            config_data = {
                'default_privacy': 'private',
                'default_playlist': None,
                'auto_thumbnail': True
            }
        
        return jsonify({
            'success': True,
            'config': config_data
        })
    
    else:  # POST
        config_data = request.json
        storage.write_text(config_key, json.dumps(config_data, indent=2))
        
        return jsonify({
            'success': True,
            'message': 'Configuration saved'
        })


if __name__ == '__main__':
    # Check for required environment variables
    required_vars = ['ZOOM_ACCOUNT_ID', 'ZOOM_CLIENT_ID', 'ZOOM_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Please set them in .env file or environment")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
