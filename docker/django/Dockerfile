# =============================================================================
# Stage 1: Builder - install Python dependencies
# =============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements/base.txt requirements/base.txt
COPY backend/requirements/prod.txt requirements/prod.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements/prod.txt

# =============================================================================
# Stage 2: Final - lean production image
# =============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Install only runtime dependencies (no gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/ .

# Collect static files at build time (uses prod settings with SECRET_KEY placeholder)
RUN DJANGO_SECRET_KEY=build-placeholder \
    POSTGRES_HOST=localhost \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Create non-root user
RUN groupadd -r django && useradd -r -g django django && \
    chown -R django:django /app
USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-tmp-dir", "/dev/shm"]
