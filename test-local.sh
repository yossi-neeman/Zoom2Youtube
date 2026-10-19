#!/bin/bash

# Quick local testing script
# Tests the Docker image locally before deploying to Lambda

echo "🧪 Testing Docker image locally..."

# Build the local image
echo "Building Dockerfile.local..."
docker build -f Dockerfile.local -t zoom2youtube:test .

echo ""
echo "✓ Build complete!"
echo ""
echo "Starting container on http://localhost:5000..."
echo "Press Ctrl+C to stop"
echo ""

# Run with local storage
docker run --rm -it \
  -p 5000:5000 \
  -v $(pwd)/recordings:/app/recordings \
  -v $(pwd)/credentials:/app/credentials \
  --env-file credentials/.env \
  -e USE_S3_STORAGE=false \
  -e PYTHONUNBUFFERED=1 \
  zoom2youtube:test
