#!/usr/bin/env bash
# =============================================================================
# deploy.sh - Build and deploy Cerisier to production
# =============================================================================
# Usage: ./scripts/deploy.sh
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

echo "========================================"
echo " Cerisier Production Deployment"
echo "========================================"
echo ""

# ---- Pre-flight checks ----
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    echo "ERROR: .env file not found. Copy .env.example and configure it."
    exit 1
fi

# ---- Step 1: Build frontend ----
echo "[1/5] Building frontend..."
if [ -d "${PROJECT_ROOT}/frontend" ] && [ -f "${PROJECT_ROOT}/frontend/package.json" ]; then
    cd "${PROJECT_ROOT}/frontend"
    npm ci --production=false
    npm run build
    echo "      Frontend built successfully."
else
    echo "      WARN: frontend/ not found, skipping frontend build."
fi

# ---- Step 2: Build Docker images ----
echo "[2/5] Building Docker images..."
cd "${PROJECT_ROOT}"
docker compose -f "${COMPOSE_FILE}" build --no-cache

# ---- Step 3: Run database migrations ----
echo "[3/5] Running database migrations..."
docker compose -f "${COMPOSE_FILE}" run --rm django \
    python manage.py migrate --noinput

# ---- Step 4: Collect static files ----
echo "[4/5] Collecting static files..."
docker compose -f "${COMPOSE_FILE}" run --rm django \
    python manage.py collectstatic --noinput

# ---- Step 5: Start services ----
echo "[5/5] Starting services..."
docker compose -f "${COMPOSE_FILE}" up -d

echo ""
echo "========================================"
echo " Deployment complete!"
echo "========================================"
echo ""

# ---- Print status ----
docker compose -f "${COMPOSE_FILE}" ps
