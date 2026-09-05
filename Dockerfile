FROM python:3.11-slim

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    fonts-liberation \
    fontconfig \
    wget \
    unzip \
    gcc \
    g++ \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    libwebp-dev \
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
COPY web_app.py .
COPY graphics_template.jpg .

# Copy web app directories
COPY templates/ ./templates/
COPY static/ ./static/

# Create directories for output and credentials
RUN mkdir -p /app/recordings /app/credentials

# Set environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Expose port for web app
EXPOSE 5000

# Default command (runs web app, can be overridden for CLI)
CMD ["python", "web_app.py"]
