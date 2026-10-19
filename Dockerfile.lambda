FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies including FreeType development files
RUN yum install -y \
    fontconfig \
    wget \
    unzip \
    gcc \
    gcc-c++ \
    libjpeg-turbo-devel \
    zlib-devel \
    freetype-devel \
    freetype \
    && yum clean all

# Install David Libre Hebrew font
RUN mkdir -p /usr/share/fonts/truetype/david-libre && \
    wget -q https://github.com/google/fonts/raw/main/ofl/davidlibre/DavidLibre-Regular.ttf \
    -O /usr/share/fonts/truetype/david-libre/DavidLibre-Regular.ttf && \
    fc-cache -f -v

# Fallback Hebrew font
RUN mkdir -p ${LAMBDA_TASK_ROOT}/fonts && \
    cd ${LAMBDA_TASK_ROOT}/fonts && \
    (wget -q -O NotoSansHebrew-Regular.ttf \
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanshebrew/NotoSansHebrew%5Bwdth%2Cwght%5D.ttf" || \
    wget -q -O NotoSansHebrew-Regular.ttf \
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansHebrew/NotoSansHebrew-Regular.ttf" || \
    echo "Font download failed, will use runtime download fallback") && \
    ls -lh ${LAMBDA_TASK_ROOT}/fonts/ && \
    echo "Font installation attempt complete"

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies (with SSL certificate handling)
# Pillow must come from a prebuilt wheel: a source build links the system FreeType 2.8,
# which lacks FT_Set_Named_Instance and breaks ImageFont.truetype().
RUN pip install --no-cache-dir --only-binary=Pillow --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application files
COPY zoom_downloader.py ${LAMBDA_TASK_ROOT}/
COPY youtube_uploader.py ${LAMBDA_TASK_ROOT}/
COPY zoom_to_youtube.py ${LAMBDA_TASK_ROOT}/
COPY storage.py ${LAMBDA_TASK_ROOT}/
COPY web_app.py ${LAMBDA_TASK_ROOT}/
COPY graphics_template.jpg ${LAMBDA_TASK_ROOT}/
COPY version.py ${LAMBDA_TASK_ROOT}/

# Copy web app directories
COPY templates/ ${LAMBDA_TASK_ROOT}/templates/
COPY static/ ${LAMBDA_TASK_ROOT}/static/

# Copy Lambda handler
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Create directories for temp storage
RUN mkdir -p /tmp/recordings /tmp/credentials

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Lambda handler
CMD ["lambda_handler.handler"]
