#!/bin/bash
# Wrapper script to run the full Zoom to YouTube workflow

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run setup first."
    echo "Run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

# Run the main script
./venv/bin/python3 zoom_to_youtube.py "$@"
