# Web Application Guide

Zoom to YouTube now includes a beautiful web interface that works on both desktop and mobile devices!

## Features

- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🚀 **One-step Publish** - Pick מסכת, דף and playlist once; the Zoom download and YouTube upload run as a single job
- 📥 **Browse Recordings** - Choose a Zoom recording from the last 1-30 days (the latest is pre-selected)
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

### 1. Publish Tab

- **Enter מסכת and דף** - the title (`מסכת | דף | בית כנסת נריה`) and thumbnail (`מסכת - דף`) are generated from them
- **Select playlist**: Optionally add to a playlist
- **Pick the Zoom recording**: the last 1, 5, 7, or 30 days; the most recent is pre-selected
- **Choose privacy / description** (optional)
- **Click "Download & Upload to YouTube"** - the server downloads the recording, uploads it and
  deletes the file; the page shows progress and the video link when done

### 2. Settings Tab

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
- `POST /api/publish` - Download a recording and upload it to YouTube (background job, see below)
- `GET /api/publish/<job_id>` - Progress of a publish job
- `GET /api/playlists` - List YouTube playlists
- `POST /api/thumbnail/preview` - Generate thumbnail preview
- `GET/POST /api/config` - Get/update configuration
- `POST /api/download`, `POST /api/upload` - The two halves of publish, kept for older clients

### Publishing from a script or cron

Set `API_TOKEN` (24+ characters) on the server and send it as a bearer token; it is accepted on
`/api/*` only. `POST /api/publish` returns immediately with a job; poll it until `status` is
`succeeded` or `failed`.

```bash
curl -sS -X POST "$Z2Y_URL/api/publish" \
  -H "Authorization: Bearer $Z2Y_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"masechet": "חולין", "daf": "קיט", "playlist_id": "PL..."}'
# -> {"success": true, "deduplicated": false, "job": {"id": "abc", "status": "queued", ...}}

curl -sS "$Z2Y_URL/api/publish/abc" -H "Authorization: Bearer $Z2Y_API_TOKEN"
# -> {"success": true, "job": {"status": "succeeded", "video_url": "https://www.youtube.com/watch?v=..."}}
```

Body fields: `masechet`, `daf` (required); `playlist_id`; `recording_id` (default: the most recent
recording with an MP4 in the last `days`); `days` (default 2, max 30); `description`; `privacy`
(`public` default, `unlisted`, `private`); `force`.

A recording is published at most once: calling again returns the running or finished job
(`"deduplicated": true`), so a retried or double-fired cron is harmless. Pass `"force": true` to
publish a recording again on purpose. Job status is kept in memory, so a server restart makes
`GET /api/publish/<id>` return 404 - then check YouTube Studio / re-POST (what was already
published is remembered across restarts).

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
