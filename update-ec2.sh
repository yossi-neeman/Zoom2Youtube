#!/bin/bash
# Update Zoom2Youtube Docker container on EC2 with authentication

set -e

EC2_IP="3.125.153.243"
SSH_KEY="/Users/yossin/workspace/Zoom2Youtube/yossineemanw-fra.pem"

echo "=== Updating Zoom2Youtube on EC2 ==="

# Update credentials/.env file on EC2 with authentication variables
echo "Uploading updated .env file..."
scp -i "$SSH_KEY" credentials/.env ubuntu@$EC2_IP:~/zoom2youtube/credentials/.env

# Pull latest image and restart container
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'EOF'
cd ~/zoom2youtube

echo "Pulling latest Docker image..."
docker pull neeman2019/zoom2youtube:latest

echo "Stopping current container..."
docker stop zoom2youtube || true

echo "Removing old container..."
docker rm zoom2youtube || true

echo "Starting new container with authentication..."
docker run -d \
  --name zoom2youtube \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest

echo ""
echo "Waiting for container to start..."
sleep 3

echo ""
echo "Container status:"
docker ps | grep zoom2youtube

echo ""
echo "Recent logs:"
docker logs --tail 10 zoom2youtube
EOF

echo ""
echo "=== Update complete! ==="
echo "Access your app at: http://$EC2_IP:5000"
echo "Username: admin"
echo "Password: Zoom2024!"
