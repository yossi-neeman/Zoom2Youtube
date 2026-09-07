# Zoom2Youtube

Automated tool to download Zoom recordings and upload them to YouTube with custom Hebrew thumbnails.

## Features

- 📥 **Download Zoom recordings** (MP4 files only)
- 📤 **Upload to YouTube** with custom privacy settings
- 🎨 **Generate Hebrew thumbnails** with custom text (David Libre font)
- 📋 **Add to YouTube playlists**
- 🌐 **Web interface** for easy management
- 🐳 **Docker support** for easy deployment
- 🔄 **Smart caching** - reuses downloaded files
- 🧹 **Auto-cleanup** - deletes files after upload
- 📊 **Progress tracking** with visual feedback

## Quick Start

### Web Interface (Recommended)

```bash
# Using Docker
docker run -d -p 5000:5000 \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest

# Access at http://localhost:5000
```

### Command Line

```bash
# Clone repository
git clone https://github.com/yossi-neeman/Zoom2Youtube.git
cd Zoom2Youtube

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
./run_zoom_to_youtube.sh
```

## Setup Guides

📖 **Installation & Setup:**
- [Local Setup](INSTALL.md) - Install dependencies and configure credentials
- [Web App Guide](WEB_APP.md) - Use the web interface
- [Docker Guide](DOCKER.md) - Run with Docker

☁️ **Cloud Deployment:**
- [AWS EC2 Deployment](AWS_DEPLOYMENT.md) - Deploy to AWS free tier ⭐ **NEW**
- [Security Guide](SECURITY.md) - Secure your public deployment ⭐ **NEW**

🔧 **Configuration:**
- [Zoom Setup](SETUP_GUIDE.md) - Get Zoom API credentials
- [YouTube Setup](YOUTUBE_SETUP.md) - Configure YouTube OAuth
- [Playlist Setup](PLAYLIST_SETUP.md) - Manage YouTube playlists

## Usage

### Web Interface

1. **Download** - Select and download recordings from Zoom
2. **Upload** - Set title, playlist, thumbnail text
3. **Complete** - Video uploaded and local file deleted

### CLI Script

```bash
./run_zoom_to_youtube.sh
```

Interactively:
1. Lists recordings from today (or past 5 days)
2. Select recording to download
3. Enter video title and thumbnail text
4. Choose privacy and playlist
5. Uploads to YouTube with custom thumbnail

## Configuration Files

```
credentials/
├── .env                    # Zoom API credentials
├── client_secrets.json     # YouTube OAuth config
└── youtube_token.pickle    # YouTube auth token (generated)

recordings/                 # Downloaded videos (auto-deleted after upload)

graphics_template.jpg       # Thumbnail template
```

### Environment Variables

Create `credentials/.env`:
```bash
ZOOM_ACCOUNT_ID=your-account-id
ZOOM_CLIENT_ID=your-client-id
ZOOM_CLIENT_SECRET=your-client-secret
```

## Docker

### Quick Run

```bash
docker pull neeman2019/zoom2youtube:latest

docker run -d \
  --name zoom2youtube \
  -p 5000:5000 \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest
```

### Docker Compose

```bash
# Web interface
docker-compose up -d

# CLI script
docker-compose run --rm cli
```

## Deployment

### AWS EC2 Free Tier

Deploy to AWS for external web access:

```bash
./deploy-to-ec2.sh
```

See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for full guide.

**Alternative Options:**
- AWS Lightsail ($3.50/month, 3 months free)
- Oracle Cloud (Always free tier)
- Any VPS with Docker support

## Requirements

- Python 3.9+
- Docker (optional, recommended)
- Zoom Server-to-Server OAuth app
- Google Cloud Project with YouTube Data API v3

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **APIs:** Zoom API, YouTube Data API v3
- **Image Processing:** Pillow (PIL)
- **Fonts:** David Libre (Hebrew)
- **Deployment:** Docker, Docker Compose

## Project Structure

```
Zoom2Youtube/
├── zoom_downloader.py      # Zoom API integration
├── youtube_uploader.py     # YouTube API integration
├── zoom_to_youtube.py      # Main CLI script
├── web_app.py             # Flask web application
├── templates/
│   └── index.html         # Web UI
├── static/                # Web assets
├── credentials/           # API credentials (gitignored)
├── recordings/            # Downloaded videos (gitignored)
├── Dockerfile            # Docker image
├── docker-compose.yml    # Multi-service setup
└── requirements.txt      # Python dependencies
```

## Scripts

- `run_zoom_download.sh` - Download recordings only
- `run_zoom_to_youtube.sh` - Full workflow (download + upload)
- `run_web_app.sh` - Start web interface
- `refresh_youtube_auth.sh` - Refresh YouTube token
- `deploy-to-ec2.sh` - Deploy to AWS EC2

## Features in Detail

### Smart Download
- Downloads only MP4 files
- Shows recordings from today, or past 5 days if none today
- Skips re-downloading existing files
- Progress indicators

### YouTube Upload
- Custom video title and description
- Privacy settings (private/unlisted/public)
- Add to specific playlist
- Custom Hebrew thumbnail with David Libre font
- Auto-cleanup after successful upload

### Web Interface
- Responsive design (desktop + mobile)
- Real-time progress tracking
- Recording management
- Playlist selection
- Thumbnail preview
- Success confirmation with "View on YouTube" link

### Docker Support
- Multi-platform (amd64 + arm64)
- Auto-built with GitHub Actions
- Published to Docker Hub
- Includes all fonts and dependencies

## Troubleshooting

### YouTube Authentication Issues

```bash
# Refresh token
./refresh_youtube_auth.sh

# Or manually
rm credentials/youtube_token.pickle
python3 zoom_to_youtube.py
```

### Docker Port Conflict

```bash
# Use different port
docker run -p 8080:5000 ...
# Access at http://localhost:8080
```

### Missing Hebrew Font

Font is included in Docker image. For local:
```bash
# macOS
brew install font-david-libre

# Ubuntu/Debian
sudo apt-get install fonts-david-libre
```

## Security

For public deployment, see [SECURITY.md](SECURITY.md):
- ✅ Basic authentication
- ✅ HTTPS with Let's Encrypt
- ✅ Firewall configuration
- ✅ AWS Security Groups
- ✅ Regular backups

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Author

Yossi Neeman

## Links

- **GitHub:** https://github.com/yossi-neeman/Zoom2Youtube
- **Docker Hub:** https://hub.docker.com/r/neeman2019/zoom2youtube
- **Issues:** https://github.com/yossi-neeman/Zoom2Youtube/issues

---

## Changelog

### v2.0 (Latest)
- ✨ Web interface with responsive design
- 🐳 Docker support with multi-platform builds
- ☁️ AWS EC2 deployment guide
- 🔒 Security best practices guide
- 🎯 Smart download with existing file detection
- 🧹 Auto-cleanup after upload
- 📊 Progress tracking and visual feedback

### v1.0
- Initial release with CLI workflow
- Zoom recording download
- YouTube upload with thumbnails
- Hebrew text support
