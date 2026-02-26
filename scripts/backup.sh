#!/usr/bin/env bash
# =============================================================================
# backup.sh - Backup PostgreSQL database from production
# =============================================================================
# Usage: ./scripts/backup.sh
# Stores timestamped gzipped SQL dumps in backups/ and keeps the last 7.
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
BACKUP_DIR="${PROJECT_ROOT}/backups"
RETENTION_DAYS=7

# Read database credentials from .env (fallback to defaults)
POSTGRES_DB="${POSTGRES_DB:-cerisier}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Generate timestamped filename
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/cerisier_${TIMESTAMP}.sql.gz"

echo "========================================"
echo " Cerisier Database Backup"
echo "========================================"
echo ""
echo "Database: ${POSTGRES_DB}"
echo "Timestamp: ${TIMESTAMP}"
echo ""

# ---- Perform backup ----
echo "Creating backup..."
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
    pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-acl \
    | gzip > "${BACKUP_FILE}"

# Verify backup was created and is not empty
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file is empty or was not created."
    rm -f "${BACKUP_FILE}"
    exit 1
fi

BACKUP_SIZE="$(du -h "${BACKUP_FILE}" | cut -f1)"
echo "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# ---- Cleanup old backups ----
echo ""
echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
DELETED_COUNT=0
while IFS= read -r old_backup; do
    rm -f "${old_backup}"
    DELETED_COUNT=$((DELETED_COUNT + 1))
    echo "  Removed: $(basename "${old_backup}")"
done < <(find "${BACKUP_DIR}" -name "cerisier_*.sql.gz" -type f -mtime +${RETENTION_DAYS} 2>/dev/null)

if [ "${DELETED_COUNT}" -eq 0 ]; then
    echo "  No old backups to remove."
fi

# ---- Summary ----
TOTAL_BACKUPS="$(find "${BACKUP_DIR}" -name "cerisier_*.sql.gz" -type f | wc -l)"
echo ""
echo "========================================"
echo " Backup complete!"
echo " File: ${BACKUP_FILE}"
echo " Size: ${BACKUP_SIZE}"
echo " Total backups on disk: ${TOTAL_BACKUPS}"
echo "========================================"
