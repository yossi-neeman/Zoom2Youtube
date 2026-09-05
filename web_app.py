#!/usr/bin/env python3
"""
Zoom to YouTube Web Application
"""

import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from zoom_downloader import ZoomRecordingDownloader
from youtube_uploader import YouTubeUploader
from zoom_to_youtube import create_thumbnail

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
CORS(app)

# Configuration
UPLOAD_FOLDER = 'recordings'
CREDENTIALS_FOLDER = 'credentials'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB max

# Ensure directories exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
Path(CREDENTIALS_FOLDER).mkdir(exist_ok=True)
Path('static').mkdir(exist_ok=True)
Path('templates').mkdir(exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/recordings', methods=['GET'])
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
def get_playlists():
    """Get YouTube playlists"""
    try:
        client_secrets_path = os.path.join(CREDENTIALS_FOLDER, 'client_secrets.json')
        if not os.path.exists(client_secrets_path):
            return jsonify({
                'success': False,
                'error': 'YouTube credentials not found. Please add client_secrets.json to credentials folder.'
            }), 500
        
        youtube_uploader = YouTubeUploader(client_secrets_file=client_secrets_path)
        playlists = youtube_uploader.list_playlists()
        
        # list_playlists() already returns simplified dictionaries with 'id', 'title', 'item_count'
        return jsonify({
            'success': True,
            'playlists': playlists
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
def upload_to_youtube():
    """Upload video to YouTube"""
    try:
        data = request.json
        
        video_file = data.get('video_file')
        title = data.get('title')
        description = data.get('description', '')
        playlist_id = data.get('playlist_id')
        thumbnail_text = data.get('thumbnail_text')
        privacy = data.get('privacy', 'private')
        
        if not video_file or not title:
            return jsonify({
                'success': False,
                'error': 'Video file and title required'
            }), 400
        
        # Generate thumbnail if text provided
        thumbnail_file = None
        if thumbnail_text:
            thumbnail_file = f'temp_thumbnail_{datetime.now().timestamp()}.jpg'
            create_thumbnail(
                thumbnail_text,
                thumbnail_file,
                'graphics_template.jpg'
            )
        
        # Upload to YouTube
        client_secrets_path = os.path.join(CREDENTIALS_FOLDER, 'client_secrets.json')
        if not os.path.exists(client_secrets_path):
            return jsonify({
                'success': False,
                'error': 'YouTube credentials not found'
            }), 500
        
        youtube_uploader = YouTubeUploader(client_secrets_file=client_secrets_path)
        video_id = youtube_uploader.upload_video(
            video_file=video_file,
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
        if os.path.exists(video_file):
            try:
                # Get the directory containing the video
                video_dir = os.path.dirname(video_file)
                
                # Remove the entire recording directory
                if video_dir and os.path.exists(video_dir) and video_dir.startswith(app.config['UPLOAD_FOLDER']):
                    shutil.rmtree(video_dir)
                    print(f"✓ Cleaned up recording directory: {video_dir}")
                else:
                    # Fallback: just remove the file
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/thumbnail/preview', methods=['POST'])
def preview_thumbnail():
    """Generate thumbnail preview"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text required'}), 400
        
        # Generate preview
        preview_file = f'static/preview_{datetime.now().timestamp()}.jpg'
        create_thumbnail(text, preview_file, 'graphics_template.jpg')
        
        return jsonify({
            'success': True,
            'preview_url': f'/{preview_file}'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update configuration"""
    config_file = os.path.join(CREDENTIALS_FOLDER, 'web_config.json')
    
    if request.method == 'GET':
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
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
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
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
