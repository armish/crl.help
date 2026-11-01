#!/bin/bash
set -euo pipefail

echo "======================================"
echo "Starting CRL.help Application"
echo "======================================"

# Resolve relative DATABASE_PATH values from the API's working directory too.
# Otherwise startup writes /app/data/... while Uvicorn reads /app/backend/data/....
cd /app/backend

# A failed download or empty snapshot must fail the deployment, not create an
# empty database that the web service can mistakenly report as healthy.
export DATABASE_PATH="${DATABASE_PATH:-/app/backend/data/crl_explorer.duckdb}"
python /app/backend/prepare_database.py
chown appuser:appuser "$DATABASE_PATH" "$(dirname "$DATABASE_PATH")"
chmod 644 "$DATABASE_PATH"

echo ""
echo "Environment Configuration:"
echo "  DATABASE_PATH: $DATABASE_PATH"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:+***SET***}"
echo "  LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo "  CORS_ORIGINS: ${CORS_ORIGINS:-*}"
echo ""

# Verify backend is ready
echo "Verifying backend setup..."
python -c "from app.config import get_settings; print('✓ Backend configuration loaded')" || {
    echo "✗ Backend configuration failed"
    exit 1
}

echo ""
echo "Starting services with Supervisor..."
echo "  - Nginx (port 80)"
echo "  - FastAPI Backend (port 8000)"
echo ""

# Start supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
