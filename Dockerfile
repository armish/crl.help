# Multi-stage build for CRL.help application
# Stage 1: Build frontend
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./
COPY frontend/.npmrc ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy frontend source
COPY frontend/ ./

# Set API base URL for production build
# In production, the frontend will use relative URLs since both are served from the same domain
ENV VITE_API_BASE_URL=""

# Build frontend for production
RUN npm run build

# Stage 2: Final production image
FROM python:3.11-slim

# Install nginx and supervisor
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend application
COPY backend/ ./backend/

# Copy frontend build from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/sites-available/default

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Create data directory
RUN mkdir -p /app/backend/data && chown -R appuser:appuser /app

# Environment variables
ENV DATABASE_URL="" \
    DATABASE_PATH=/app/backend/data/crl_explorer.duckdb \
    OPENAI_API_KEY="sk-dummy-key-for-dry-run-mode" \
    AI_DRY_RUN=true \
    CORS_ORIGINS="*" \
    LOG_LEVEL=INFO \
    PORT=8000

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost/api/health || exit 1

# Run startup script
CMD ["/start.sh"]
