# ==============================================================================
#  AI-NAS Backend Server - Dockerfile
#  Platform: amd64 (Windows dev / Linux production)
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libffi-dev && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime

LABEL maintainer="AI-NAS Team" description="AI-NAS Backend Server" version="2.0"

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 tini curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN mkdir -p /app/config /app/data /app/logs /nas

WORKDIR /app

# Copy backend application (exclude venv, __pycache__, .pyc)
COPY backend/ .

# Copy frontend
COPY frontend/ ./static/

# Copy configuration files
COPY config/ ./config/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -sf http://localhost:8000/health || exit 1

VOLUME ["/app/data", "/app/logs", "/nas"]

ENTRYPOINT ["tini", "--"]

CMD ["python", "main.py"]