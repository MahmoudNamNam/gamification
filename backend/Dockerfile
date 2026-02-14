# Multi-stage build for FastAPI application (Linux amd64)
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt gunicorn

# Production stage
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY app/ ./app/
COPY scripts/ ./scripts/

RUN mkdir -p uploads

# Non-secret defaults only; override with --env-file or platform variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MONGODB_DB_NAME=khaleeji \
    CORS_ORIGINS="*" \
    JWT_ALGORITHM=HS256

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, httpx; port=os.environ.get('PORT','8000'); httpx.get(f'http://localhost:{port}/health', timeout=5)" || exit 1

CMD ["sh", "-c", "gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --timeout 180"]
