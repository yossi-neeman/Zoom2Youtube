FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    fonts-liberation \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install David Libre Hebrew font
RUN mkdir -p /usr/share/fonts/truetype/david-libre && \
    wget -q https://github.com/google/fonts/raw/main/ofl/davidlibre/DavidLibre-Regular.ttf \
    -O /usr/share/fonts/truetype/david-libre/DavidLibre-Regular.ttf && \
    fc-cache -f -v

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY zoom_downloader.py .
COPY youtube_uploader.py .
COPY zoom_to_youtube.py .
COPY graphics_template.jpg .

# Create directories for output and credentials
RUN mkdir -p /app/recordings /app/credentials

# Set environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "zoom_to_youtube.py"]
