#!/bin/bash
# Build script for Docker image

set -e

echo "Building Zoom2Youtube Docker image..."
docker build -t zoom2youtube .

echo ""
echo "✓ Docker image built successfully!"
echo ""
echo "To run locally:"
echo "  docker run -it --rm \\"
echo "    -v \$(pwd)/credentials:/app/credentials \\"
echo "    -v \$(pwd)/recordings:/app/recordings \\"
echo "    -e ENV_FILE=/app/credentials/.env \\"
echo "    zoom2youtube"
echo ""
echo "See DOCKER.md for EC2 deployment instructions."
