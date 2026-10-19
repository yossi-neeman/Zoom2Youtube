# Zoom2Youtube - Quick Start Guide

Automatically download Zoom recordings and upload them to YouTube with custom Hebrew thumbnails.

## 🚀 Quick Start

### Option 1: Docker Compose (Easiest)

```bash
# 1. Clone and navigate
git clone <your-repo>
cd Zoom2Youtube

# 2. Set up credentials (see Configuration section)
# Edit credentials/.env with your Zoom and auth credentials

# 3. Run
docker-compose up

# 4. Open http://localhost:5000
```

### Option 2: Python (Local Development)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up credentials
# Edit credentials/.env

# 3. Run
python web_app.py

# 4. Open http://localhost:5000
```

### Option 3: AWS Lambda (Production - Pay per Use)

```bash
# One-command deployment
./deploy-lambda.sh

# Follow the prompts - it will:
# - Create S3 bucket
# - Build and push Docker image
# - Deploy Lambda function
# - Give you a public URL
```

**Cost**: ~$0.50/month for 10 min/day usage vs $7-10/month for EC2 💰

## 📋 Configuration

### 1. Create credentials/.env

```bash
# Zoom OAuth Credentials (get from https://marketplace.zoom.us/)
ZOOM_ACCOUNT_ID=your-account-id
ZOOM_CLIENT_ID=your-client-id
ZOOM_CLIENT_SECRET=your-client-secret

# Web Authentication
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=YourSecurePassword123
```

### 2. Add YouTube Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Download as `credentials/client_secrets.json`

### 3. (Optional) Add Graphics Template

Place your thumbnail template as `graphics_template.jpg` in the root directory.

## 🎯 Features

- **Download** Zoom recordings with one click
- **Upload** to YouTube with custom titles
- **Hebrew thumbnails** - automatically generated
- **Playlist management** - remembers your last selection
- **Auto-cleanup** - deletes recordings after upload
- **Multiple deployment** options - local, Docker, or Lambda

## 🔄 Deployment Options Comparison

| Feature | Local/Docker | AWS Lambda |
|---------|-------------|------------|
| **Cost** | $7-10/month (EC2) | $0.50/month (10min/day) |
| **Scaling** | Manual | Automatic |
| **Maintenance** | You manage server | AWS managed |
| **Storage** | Local filesystem | S3 (unlimited) |
| **Cold start** | None | 3-5 seconds |
| **Max runtime** | Unlimited | 15 minutes |
| **Best for** | Development, heavy use | Production, light use |

## 🐳 Docker Commands

```bash
# Local development with hot reload
docker-compose up

# Test production build locally
./test-local.sh

# Build for Lambda
docker build -t zoom2youtube:lambda .

# Build for local
docker build -f Dockerfile.local -t zoom2youtube:local .
```

## ☁️ Lambda Management

```bash
# Deploy/Update
./deploy-lambda.sh

# View logs
aws logs tail /aws/lambda/zoom2youtube --follow

# Update environment variables
aws lambda update-function-configuration \
  --function-name zoom2youtube \
  --environment "Variables={USE_S3_STORAGE=true,S3_BUCKET=your-bucket,...}"
```

## 📖 Full Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide with all options
- **[Architecture](#architecture)** - How it works
- **[Troubleshooting](#troubleshooting)** - Common issues

## 🏗️ Architecture

### Local Mode
```
User → Flask App → Local Filesystem
                 → YouTube API
                 → Zoom API
```

### Lambda Mode
```
User → Lambda Function URL → Flask App → S3 Storage
                                       → YouTube API
                                       → Zoom API
```

The **storage abstraction layer** (`storage.py`) automatically switches between local filesystem and S3 based on the `USE_S3_STORAGE` environment variable.

## 🔧 Troubleshooting

### "Credentials not found"
```bash
# For local:
ls -la credentials/client_secrets.json

# For Lambda:
aws s3 ls s3://your-bucket/zoom2youtube/credentials/
```

### Docker build fails
```bash
# Clear Docker cache
docker system prune -a

# Rebuild
docker-compose build --no-cache
```

### Lambda timeout
```bash
# Increase timeout (max 900 seconds)
aws lambda update-function-configuration \
  --function-name zoom2youtube \
  --timeout 900
```

### Port 5000 already in use
```bash
# Find and kill process
lsof -ti:5000 | xargs kill -9

# Or change port in docker-compose.yml
```

## 🔐 Security

- Never commit credentials to git
- Use strong passwords for AUTH_PASSWORD
- Keep boto3 and dependencies updated
- For production, consider:
  - AWS Secrets Manager for credentials
  - VPC for Lambda
  - CloudFront for DDoS protection
  - Rate limiting

## 🤝 Contributing

1. Make changes locally
2. Test with `./test-local.sh`
3. Test Lambda deployment in a separate AWS account
4. Submit PR

## 📝 License

[Your License Here]

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Questions**: [Your contact]

---

**Made with ❤️ for easy Zoom → YouTube workflow**
