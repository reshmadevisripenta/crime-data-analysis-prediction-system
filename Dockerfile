# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies for MySQL, Pillow, ReportLab, and Python builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and install python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy entrypoint script and ensure Unix line endings
COPY entrypoint.sh /app/entrypoint.sh
RUN tr -d '\r' < /app/entrypoint.sh > /app/entrypoint_unix.sh && \
    mv /app/entrypoint_unix.sh /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Copy project source code
COPY . /app/

# Create media and static output directories
RUN mkdir -p /app/media /app/staticfiles /app/media/trained_models /app/media/reports /app/media/avatars

# Expose Django port
EXPOSE 8000

# Entrypoint script handles migrations and starts gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "config.wsgi:application"]
