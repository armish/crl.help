#!/bin/bash
set -e

echo "======================================"
echo "Starting CRL.help Application"
echo "======================================"

# Download database if DATABASE_URL is provided
if [ -n "$DATABASE_URL" ]; then
    echo "Downloading database from: $DATABASE_URL"

    # Create data directory if it doesn't exist
    mkdir -p /app/backend/data

    # Download the database
    if curl -L -f -o "$DATABASE_PATH" "$DATABASE_URL"; then
        echo "✓ Database downloaded successfully to $DATABASE_PATH"

        # Check file size
        DB_SIZE=$(du -h "$DATABASE_PATH" | cut -f1)
        echo "  Database size: $DB_SIZE"

        # Set proper permissions
        chown appuser:appuser "$DATABASE_PATH"
        chmod 644 "$DATABASE_PATH"
    else
        echo "✗ Failed to download database from $DATABASE_URL"
        echo "  Starting application without database..."
    fi
else
    echo "No DATABASE_URL provided. Checking for existing database..."

    if [ -f "$DATABASE_PATH" ]; then
        DB_SIZE=$(du -h "$DATABASE_PATH" | cut -f1)
        echo "✓ Found existing database at $DATABASE_PATH (size: $DB_SIZE)"
    else
        echo "⚠ Warning: No database found at $DATABASE_PATH"
        echo "  Application will start but may not function correctly."
        echo "  Please provide DATABASE_URL environment variable or mount a database file."
    fi
fi

echo ""
echo "Environment Configuration:"
echo "  DATABASE_PATH: $DATABASE_PATH"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:+***SET***}"
echo "  LOG_LEVEL: $LOG_LEVEL"
echo "  CORS_ORIGINS: $CORS_ORIGINS"
echo ""

# Verify backend is ready
echo "Verifying backend setup..."
cd /app/backend
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
