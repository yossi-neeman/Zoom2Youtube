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
COPY storage.py .
COPY web_app.py .
COPY graphics_template.jpg .

# Copy web app directories
COPY templates/ ./templates/
COPY static/ ./static/

# Copy version.py last to avoid cache issues
COPY version.py .

# Create directories for output and credentials, and run as a non-root user
# (uid 1000 matches the default user on a Raspberry Pi so bind-mounted dirs stay writable)
RUN useradd --create-home --uid 1000 app && \
    mkdir -p /app/recordings /app/credentials && \
    chown -R app:app /app
USER app

# Set environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=5000

# Expose port for web app
EXPOSE 5000

# Production server: gunicorn, not the Flask dev server (no debugger).
# A single worker is intentional: upload de-duplication and the login rate limiter
# are in-memory. Threads handle concurrency; the long timeout allows large uploads.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 3600 web_app:app"]
