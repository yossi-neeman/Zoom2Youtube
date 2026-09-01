#!/usr/bin/env python3
"""
Zoom to YouTube Web Application
"""

import os
import json
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
        
        zoom_downloader = ZoomRecordingDownloader()
        
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
        
        zoom_downloader = ZoomRecordingDownloader()
        
        # Download logic here
        # This is a simplified version - you'd need to implement the full download
        
        return jsonify({
            'success': True,
            'message': 'Download started',
            'file_path': 'path/to/downloaded/file.mp4'
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
        youtube_uploader = YouTubeUploader()
        playlists = youtube_uploader.list_playlists()
        
        return jsonify({
            'success': True,
            'playlists': [
                {
                    'id': pl['id'],
                    'title': pl['snippet']['title'],
                    'item_count': pl['contentDetails']['itemCount']
                }
                for pl in playlists
            ]
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
        youtube_uploader = YouTubeUploader()
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
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_url': f'https://www.youtube.com/watch?v={video_id}'
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
