#!/bin/bash
# Wrapper script to run the web application

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run setup first."
    echo "Run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
elif [ -f credentials/.env ]; then
    export $(grep -v '^#' credentials/.env | grep -v '^$' | xargs)
fi

echo "======================================================================" 
echo "Zoom to YouTube - Web Application"
echo "======================================================================"
echo ""
echo "Starting web server..."
echo "Access the application at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================================================" 
echo ""

# Run the web application
./venv/bin/python3 web_app.py
