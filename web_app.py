#!/usr/bin/env python3
"""
Zoom to YouTube Web Application
"""

import os
import json
import shutil
import threading
import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, flash, make_response, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

from zoom_downloader import ZoomRecordingDownloader
from youtube_uploader import YouTubeUploader
from zoom_to_youtube import create_thumbnail
from version import get_full_version, VERSION
from storage import get_storage

app = Flask(__name__)
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    print("Warning: SECRET_KEY is not set; using a random key (sessions reset on every restart)")
    _secret_key = os.urandom(24).hex()
app.secret_key = _secret_key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['JSON_AS_ASCII'] = False  # Allow Unicode characters in JSON responses

# Session cookie hardening. Set SESSION_COOKIE_SECURE=true when served over HTTPS.
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

# Behind a reverse proxy / tunnel (Cloudflare Tunnel, nginx, ...) trust one hop of
# X-Forwarded-* so request.remote_addr is the real client (used by the login limiter).
if os.environ.get('TRUST_PROXY', 'false').lower() == 'true':
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# The UI is served from the same origin, so CORS is off unless origins are listed explicitly.
_cors_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]
if _cors_origins:
    CORS(app, origins=_cors_origins)

# Debug-only endpoints/UI (thumbnail tester) are disabled unless explicitly enabled.
DEBUG_ENDPOINTS_ENABLED = os.environ.get('ENABLE_DEBUG_ENDPOINTS', 'false').lower() == 'true'

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

# Admin sign-in method: 'password' (default), 'google', or 'both'.
# Google sign-in only identifies the admin (scopes: openid email profile); it is unrelated
# to the central YouTube account that videos are uploaded to.
AUTH_MODE = os.environ.get('AUTH_MODE', 'password').lower()
GOOGLE_LOGIN_CLIENT_ID = os.environ.get('GOOGLE_LOGIN_CLIENT_ID', '')
GOOGLE_LOGIN_CLIENT_SECRET = os.environ.get('GOOGLE_LOGIN_CLIENT_SECRET', '')
GOOGLE_LOGIN_REDIRECT_URI = os.environ.get('GOOGLE_LOGIN_REDIRECT_URI', '')  # default: derived from request
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip()}
ADMIN_DOMAINS = {d.strip().lower().lstrip('@') for d in os.environ.get('ADMIN_DOMAINS', '').split(',') if d.strip()}
GOOGLE_LOGIN_SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email',
                       'https://www.googleapis.com/auth/userinfo.profile']

# Login brute-force protection: too many failures from one IP -> temporary lockout.
# In-memory (per process); the container runs a single gunicorn worker.
LOGIN_MAX_FAILURES = int(os.environ.get('LOGIN_MAX_FAILURES', 5))
LOGIN_WINDOW_SECONDS = int(os.environ.get('LOGIN_WINDOW_SECONDS', 900))
_login_failures = defaultdict(deque)
_login_lock = threading.Lock()

# Native app sign-in: after Google sign-in in the system browser the server redirects to
# z2y://login?code=<one-time code>; the app exchanges it for a session cookie.
# In-memory (single gunicorn worker), short-lived, single use.
APP_LOGIN_SCHEME = 'z2y'
APP_LOGIN_CODE_TTL = 120
_app_login_codes = {}
_app_login_lock = threading.Lock()


def _issue_app_login_code(email, name):
    code = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _app_login_lock:
        for k in [k for k, v in _app_login_codes.items() if v[0] < now]:
            del _app_login_codes[k]
        _app_login_codes[code] = (now + APP_LOGIN_CODE_TTL, email, name)
    return code


def _redeem_app_login_code(code):
    with _app_login_lock:
        entry = _app_login_codes.pop(code, None)
    if entry and entry[0] >= time.monotonic():
        return entry[1], entry[2]
    return None


def _login_retry_after(ip):
    """Seconds until `ip` may try again, or 0 if it is not locked out."""
    now = time.monotonic()
    with _login_lock:
        failures = _login_failures[ip]
        while failures and now - failures[0] > LOGIN_WINDOW_SECONDS:
            failures.popleft()
        if len(failures) >= LOGIN_MAX_FAILURES:
            return int(LOGIN_WINDOW_SECONDS - (now - failures[0])) + 1
        return 0


def _record_login_failure(ip):
    with _login_lock:
        _login_failures[ip].append(time.monotonic())


def _clear_login_failures(ip):
    with _login_lock:
        _login_failures.pop(ip, None)


def _credentials_match(username, password):
    """Constant-time credential comparison."""
    user_ok = hmac.compare_digest((username or '').encode('utf-8'), AUTH_USERNAME.encode('utf-8'))
    pass_ok = hmac.compare_digest((password or '').encode('utf-8'), AUTH_PASSWORD.encode('utf-8'))
    return user_ok and pass_ok


def _password_login_enabled():
    return AUTH_MODE in ('password', 'both')


def _google_login_enabled():
    return AUTH_MODE in ('google', 'both') and bool(GOOGLE_LOGIN_CLIENT_ID and GOOGLE_LOGIN_CLIENT_SECRET)


def _email_allowed(email):
    """True if the (verified) email is on the admin allowlist."""
    email = (email or '').lower()
    if not email or '@' not in email:
        return False
    return email in ADMIN_EMAILS or email.rsplit('@', 1)[1] in ADMIN_DOMAINS


def _google_flow():
    from google_auth_oauthlib.flow import Flow
    redirect_uri = GOOGLE_LOGIN_REDIRECT_URI or url_for('google_callback', _external=True)
    client_config = {'web': {
        'client_id': GOOGLE_LOGIN_CLIENT_ID,
        'client_secret': GOOGLE_LOGIN_CLIENT_SECRET,
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uris': [redirect_uri],
    }}
    return Flow.from_client_config(client_config, scopes=GOOGLE_LOGIN_SCOPES, redirect_uri=redirect_uri)


def _exchange_google_code(code, code_verifier):
    """Exchange the auth code and return the verified ID-token claims."""
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    flow = _google_flow()
    flow.fetch_token(code=code, code_verifier=code_verifier)
    return google_id_token.verify_oauth2_token(
        flow.credentials.id_token, google_requests.Request(), GOOGLE_LOGIN_CLIENT_ID)


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
        if not _password_login_enabled():
            return render_template('login.html', error='Password sign-in is disabled',
                                   google_enabled=_google_login_enabled(), password_enabled=False,
                                   version=get_full_version()), 403
        username = request.form.get('username')
        password = request.form.get('password')
        ip = request.remote_addr or 'unknown'

        retry_after = _login_retry_after(ip)
        if retry_after:
            response = make_response(render_template(
                'login.html',
                error=f'Too many failed attempts. Try again in {retry_after // 60 + 1} minutes.',
                google_enabled=_google_login_enabled(), password_enabled=True,
                version=get_full_version()), 429)
            response.headers['Retry-After'] = str(retry_after)
            return response

        if _credentials_match(username, password):
            _clear_login_failures(ip)
            session.clear()
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            return redirect(url_for('index'))
        else:
            _record_login_failure(ip)
            return render_template('login.html', error='Invalid username or password',
                                   google_enabled=_google_login_enabled(), password_enabled=True,
                                   version=get_full_version())
    
    # If already logged in, redirect to index
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    return render_template('login.html', error=request.args.get('error'),
                           google_enabled=_google_login_enabled(),
                           password_enabled=_password_login_enabled(),
                           version=get_full_version())


@app.route('/auth/google')
def google_login():
    """Start Google sign-in (state + PKCE)."""
    if not AUTH_ENABLED or not _google_login_enabled():
        abort(404)
    flow = _google_flow()
    auth_url, state = flow.authorization_url(prompt='select_account', include_granted_scopes='false')
    session['google_oauth_state'] = state
    session['google_oauth_verifier'] = flow.code_verifier
    session['google_oauth_app'] = request.args.get('app') == '1'
    return redirect(auth_url)


@app.route('/auth/callback')
def google_callback():
    """Finish Google sign-in: verify state + ID token, then check the admin allowlist."""
    if not AUTH_ENABLED or not _google_login_enabled():
        abort(404)
    ip = request.remote_addr or 'unknown'
    expected_state = session.pop('google_oauth_state', None)
    verifier = session.pop('google_oauth_verifier', None)
    from_app = bool(session.pop('google_oauth_app', False))

    def _fail(message, status=403):
        return render_template('login.html', error=message, google_enabled=True,
                               password_enabled=_password_login_enabled(),
                               version=get_full_version()), status

    if _login_retry_after(ip):
        return _fail('Too many failed attempts. Try again later.', 429)
    if request.args.get('error'):
        return _fail('Google sign-in was cancelled or denied', 400)
    state = request.args.get('state', '')
    code = request.args.get('code')
    if not expected_state or not verifier or not code or not hmac.compare_digest(state, expected_state):
        _record_login_failure(ip)
        return _fail('Invalid sign-in session. Please try again.', 400)

    try:
        claims = _exchange_google_code(code, verifier)
    except Exception as e:
        print(f"Google sign-in failed: {e}")
        _record_login_failure(ip)
        return _fail('Google sign-in failed. Please try again.', 400)

    email = (claims.get('email') or '').lower()
    if not claims.get('email_verified') or not _email_allowed(email):
        _record_login_failure(ip)
        print(f"Google sign-in rejected for {email or 'unknown email'}")
        return _fail('This Google account is not authorized to use this app.')

    _clear_login_failures(ip)
    if from_app:
        session.clear()
        code = _issue_app_login_code(email, claims.get('name', email))
        print(f"Admin signed in via Google (app): {email}")
        return render_template('app_return.html', app_url=f'{APP_LOGIN_SCHEME}://login?code={code}')
    session.clear()
    session['logged_in'] = True
    session['username'] = email
    session['name'] = claims.get('name', email)
    session.permanent = True
    print(f"Admin signed in via Google: {email}")
    return redirect(url_for('index'))


@app.route('/auth/app-exchange', methods=['POST'])
def app_exchange():
    """Native app: trade the one-time code from the z2y:// redirect for a session cookie."""
    if not AUTH_ENABLED or not _google_login_enabled():
        abort(404)
    ip = request.remote_addr or 'unknown'
    if _login_retry_after(ip):
        return jsonify({'success': False, 'error': 'Too many failed attempts. Try again later.'}), 429
    code = (request.get_json(silent=True) or {}).get('code', '')
    redeemed = _redeem_app_login_code(code) if isinstance(code, str) and code else None
    if not redeemed:
        _record_login_failure(ip)
        return jsonify({'success': False, 'error': 'Sign-in expired. Please try again.'}), 400
    email, name = redeemed
    _clear_login_failures(ip)
    session.clear()
    session['logged_in'] = True
    session['username'] = email
    session['name'] = name
    session.permanent = True
    return jsonify({'success': True, 'username': email})


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
    return render_template('index.html', version=get_full_version(), username=username,
                           debug_enabled=DEBUG_ENDPOINTS_ENABLED)


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
    if not DEBUG_ENDPOINTS_ENABLED:
        abort(404)
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
    
    # Development server only; the Docker image runs gunicorn. Debug mode (Werkzeug
    # debugger = remote code execution) is opt-in via FLASK_DEBUG=true.
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host=os.environ.get('HOST', '0.0.0.0'), port=port, debug=debug)
