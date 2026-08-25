# syntax=docker/dockerfile:1
FROM python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BUS_DEV=0 \
    BUS_DB=/data/app.db

# Non-root runtime user
RUN useradd -m appuser
WORKDIR /app

# Install the reviewed, hash-locked Linux dependency graph first (better layer caching).
COPY requirements-linux.lock.txt .
RUN pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --require-hashes \
    -r requirements-linux.lock.txt

# Copy application code
COPY . .

# Data directory for SQLite persistence
RUN mkdir -p /data && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=3s --retries=10 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2).read()"]
# FastAPI app object exposed by core.api.http
CMD ["python", "-m", "uvicorn", "core.api.http:create_app", "--factory", "--host", "0.0.0.0", "--port", "8765"]
