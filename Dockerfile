# Base image with Python. "slim" keeps the image small.
FROM python:3.12-slim

# Python runs better in containers with these set:
#  - don't write .pyc files, - don't buffer stdout/stderr (logs appear live)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System packages:
#  - ffmpeg: required by the worker to transcode videos to HLS
#  - libpq5: runtime library psycopg (PostgreSQL driver) needs
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so Docker can cache this layer when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project source.
COPY . .

EXPOSE 8000

# Default command (overridden per service in docker-compose.yml).
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
