# Web Application Guide

Zoom to YouTube now includes a beautiful web interface that works on both desktop and mobile devices!

## Features

- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 📥 **Browse Recordings** - View and select Zoom recordings from the last 1-30 days
- 📤 **Easy Upload** - Upload to YouTube with a simple form
- 🖼️ **Thumbnail Generator** - Create Hebrew thumbnails with live preview
- 📋 **Playlist Management** - Add videos to playlists automatically
- ⚙️ **Settings** - Configure default privacy and preferences

## Quick Start

### Option 1: Run Locally with Python

```bash
cd /Users/yossin/workspace/Zoom2Youtube

# Install dependencies (if not already done)
./venv/bin/pip install Flask Flask-CORS

# Run the web app
./venv/bin/python3 web_app.py
```

Then open: http://localhost:5000

### Option 2: Run with Docker Compose

```bash
cd /Users/yossin/workspace/Zoom2Youtube

# Start the web app
docker-compose up web

# Access at http://localhost:5000
```

### Option 3: Run with Docker

```bash
cd /Users/yossin/workspace/Zoom2Youtube

# Build the image
docker build -t zoom2youtube .

# Run the web app
docker run -it --rm \
  -p 5000:5000 \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  -v $(pwd)/static:/app/static \
  zoom2youtube python web_app.py
```

Then open: http://localhost:5000

## Using the Web Interface

### 1. Recordings Tab

- **Select time range**: Choose to show recordings from the last 1, 5, 7, or 30 days
- **Click on a recording** to select it
- **Click "Download Selected"** to download the recording

### 2. Upload Tab

- **Enter video details**: Title (required), description (optional)
- **Choose privacy**: Private, Unlisted, or Public
- **Select playlist**: Optionally add to a playlist
- **Add thumbnail**: Enter Hebrew text and preview before uploading
- **Click "Upload to YouTube"** when ready

### 3. Settings Tab

- **Default Privacy**: Set your preferred default privacy level
- **Auto-generate Thumbnails**: Enable/disable automatic thumbnail creation

## Mobile Usage

The interface is fully responsive and optimized for mobile devices:

- **Portrait mode** - Optimized for phone screens
- **Touch-friendly** - Large buttons and easy navigation
- **Fast loading** - Lightweight and optimized

Simply access http://your-server-ip:5000 from your mobile browser!

## API Endpoints

The web app exposes REST API endpoints:

- `GET /api/recordings?days=5` - Get available recordings
- `POST /api/download` - Download a recording
- `GET /api/playlists` - List YouTube playlists
- `POST /api/upload` - Upload video to YouTube
- `POST /api/thumbnail/preview` - Generate thumbnail preview
- `GET/POST /api/config` - Get/update configuration

## Production Deployment

For production deployment:

1. **Set a secret key**:
   ```bash
   export SECRET_KEY=$(python3 -c 'import os; print(os.urandom(24).hex())')
   ```

2. **Use a production WSGI server** (e.g., Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
   ```

3. **Deploy with Docker Compose**:
   ```bash
   docker-compose up -d web
   ```

4. **Use NGINX as reverse proxy** (optional but recommended)

## Security Considerations

- The web app requires the same Zoom and YouTube credentials as the CLI
- Credentials are loaded from environment variables (`.env` file)
- For production, consider adding authentication (basic auth, OAuth, etc.)
- Use HTTPS in production (setup NGINX with Let's Encrypt)

## Troubleshooting

### Port already in use
```bash
# Change the port
PORT=8080 python web_app.py
```

### Missing credentials
Make sure your `.env` file is in the `credentials/` directory with:
```
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
```

### YouTube OAuth issues
The web app uses the same `client_secrets.json` and `youtube_token.pickle` files as the CLI version.

## Development

To run in development mode with auto-reload:

```bash
export FLASK_ENV=development
python web_app.py
```

Changes to Python files will automatically reload the server.

## Future Enhancements

Planned features:
- [ ] Real-time upload progress with WebSockets
- [ ] User authentication system
- [ ] Multi-user support
- [ ] Recording scheduling
- [ ] Batch uploads
- [ ] Mobile app (iOS/Android)
