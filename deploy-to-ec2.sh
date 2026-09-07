#!/bin/bash
# Quick deployment script for EC2

set -e

echo "======================================================================" 
echo "Zoom2Youtube - EC2 Deployment Helper"
echo "======================================================================"
echo ""

# Check if required files exist
if [ ! -f "credentials/.env" ]; then
    echo "❌ Error: credentials/.env not found"
    exit 1
fi

if [ ! -f "credentials/client_secrets.json" ]; then
    echo "❌ Error: credentials/client_secrets.json not found"
    exit 1
fi

if [ ! -f "credentials/youtube_token.pickle" ]; then
    echo "⚠️  Warning: credentials/youtube_token.pickle not found"
    echo "   You may need to authenticate YouTube on the server"
fi

# Get EC2 details
read -p "Enter EC2 Public IP: " EC2_IP
read -p "Enter path to your EC2 key file (.pem): " KEY_FILE

if [ ! -f "$KEY_FILE" ]; then
    echo "❌ Error: Key file not found: $KEY_FILE"
    exit 1
fi

# Ensure key has correct permissions
chmod 400 "$KEY_FILE"

echo ""
echo "Step 1/4: Testing SSH connection..."
if ssh -i "$KEY_FILE" -o ConnectTimeout=10 ubuntu@$EC2_IP "echo 'Connection successful'" 2>/dev/null; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    echo "   Make sure:"
    echo "   - EC2 instance is running"
    echo "   - Security group allows SSH (port 22) from your IP"
    echo "   - Key file is correct"
    exit 1
fi

echo ""
echo "Step 2/4: Creating directories on EC2..."
ssh -i "$KEY_FILE" ubuntu@$EC2_IP "mkdir -p ~/zoom2youtube/credentials"

echo ""
echo "Step 3/4: Uploading credentials..."
scp -i "$KEY_FILE" credentials/.env ubuntu@$EC2_IP:~/zoom2youtube/credentials/
scp -i "$KEY_FILE" credentials/client_secrets.json ubuntu@$EC2_IP:~/zoom2youtube/credentials/

if [ -f "credentials/youtube_token.pickle" ]; then
    scp -i "$KEY_FILE" credentials/youtube_token.pickle ubuntu@$EC2_IP:~/zoom2youtube/credentials/
    echo "✅ All credentials uploaded"
else
    echo "⚠️  Skipped youtube_token.pickle (not found)"
fi

echo ""
echo "Step 4/4: Setting up Docker and running container..."
ssh -i "$KEY_FILE" ubuntu@$EC2_IP "bash -s" << 'ENDSSH'
# Install Docker if not already installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    rm get-docker.sh
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

cd ~/zoom2youtube

# Pull latest image
echo "Pulling latest Docker image..."
docker pull neeman2019/zoom2youtube:latest

# Stop and remove existing container if it exists
docker stop zoom2youtube 2>/dev/null || true
docker rm zoom2youtube 2>/dev/null || true

# Run container
echo "Starting container..."
docker run -d \
  --name zoom2youtube \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest

# Wait for container to start
sleep 3

# Check if container is running
if docker ps | grep -q zoom2youtube; then
    echo "✅ Container is running"
else
    echo "❌ Container failed to start"
    echo "Logs:"
    docker logs zoom2youtube
    exit 1
fi
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "✅ Deployment Complete!"
    echo "======================================================================"
    echo ""
    echo "Access your web interface at:"
    echo "  http://$EC2_IP:5000"
    echo ""
    echo "To view logs:"
    echo "  ssh -i $KEY_FILE ubuntu@$EC2_IP 'docker logs -f zoom2youtube'"
    echo ""
    echo "To restart:"
    echo "  ssh -i $KEY_FILE ubuntu@$EC2_IP 'docker restart zoom2youtube'"
    echo ""
    echo "⚠️  Important Security Notes:"
    echo "  - Currently accessible from anywhere on port 5000"
    echo "  - Consider adding HTTPS and authentication"
    echo "  - See AWS_DEPLOYMENT.md for security improvements"
    echo ""
else
    echo ""
    echo "❌ Deployment failed. Check the error messages above."
    exit 1
fi
