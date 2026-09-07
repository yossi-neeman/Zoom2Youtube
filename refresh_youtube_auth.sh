#!/bin/bash
# Refresh YouTube Authentication Token

echo "======================================================================" 
echo "YouTube Authentication Refresh"
echo "======================================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check if client secrets exist
if [ ! -f "credentials/client_secrets.json" ]; then
    echo "Error: credentials/client_secrets.json not found."
    exit 1
fi

echo "Removing expired token..."
rm -f credentials/youtube_token.pickle youtube_token.pickle

echo ""
echo "Starting YouTube authentication..."
echo "A browser window will open for you to authorize the app."
echo ""

# Run authentication
./venv/bin/python3 << 'EOF'
import os
import sys

os.chdir('/Users/yossin/workspace/Zoom2Youtube')

from youtube_uploader import YouTubeUploader

try:
    print("Authenticating with YouTube...")
    uploader = YouTubeUploader(client_secrets_file='credentials/client_secrets.json')
    uploader.authenticate()
    print("\n✓ Authentication successful!")
    print("Token saved to: credentials/youtube_token.pickle")
    print("\nYou can now restart your Docker container:")
    print("  docker restart $(docker ps -q --filter ancestor=neeman2019/zoom2youtube:latest)")
except Exception as e:
    print(f"\n✗ Authentication failed: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================" 
    echo "✓ Authentication complete!"
    echo "======================================================================"
fi
