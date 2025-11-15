# Docker Deployment Guide

This guide explains how to build and deploy CRL.help using Docker.

## Quick Start

### Using Docker Compose (Recommended)

1. **Create environment file:**

```bash
cp .env.example .env
# Edit .env and add your configuration
```

2. **Configure `.env` file:**

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-api-key-here

# Optional: URL to download database (if not already present)
DATABASE_URL=https://example.com/path/to/crl_explorer.duckdb

# Optional: Override default settings
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

3. **Start the application:**

```bash
docker-compose up -d
```

4. **Access the application:**

Open your browser to http://localhost

### Using Docker CLI

```bash
docker run -d \
  -p 80:80 \
  -e DATABASE_URL=https://your-db-url/crl_explorer.duckdb \
  -e OPENAI_API_KEY=your-api-key \
  -v ./backend/data:/app/backend/data \
  ghcr.io/armish/crl.help:latest
```

## Database Configuration

The application requires a DuckDB database file. There are three ways to provide it:

### Option 1: Download on Startup (Recommended for Production)

Set the `DATABASE_URL` environment variable to automatically download the database:

```bash
DATABASE_URL=https://example.com/crl_explorer.duckdb
```

The startup script will:
1. Download the database from the URL
2. Save it to `/app/backend/data/crl_explorer.duckdb`
3. Verify the download and set proper permissions
4. Start the application

### Option 2: Mount Existing Database (Recommended for Development)

Mount a local database file using a volume:

```bash
docker run -d \
  -p 80:80 \
  -e OPENAI_API_KEY=your-api-key \
  -v /path/to/your/crl_explorer.duckdb:/app/backend/data/crl_explorer.duckdb:ro \
  ghcr.io/armish/crl.help:latest
```

### Option 3: Persistent Volume

Use a Docker volume to persist the database across container restarts:

```yaml
services:
  web:
    volumes:
      - crl-data:/app/backend/data

volumes:
  crl-data:
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | - | URL to download the DuckDB database |
| `DATABASE_PATH` | No | `/app/backend/data/crl_explorer.duckdb` | Path to DuckDB file inside container |
| `OPENAI_API_KEY` | **Yes** | - | Your OpenAI API key |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed origins |
| `OPENAI_SUMMARY_MODEL` | No | `gpt-5-nano` | Model for CRL summarization |
| `OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-large` | Model for embeddings |
| `OPENAI_QA_MODEL` | No | `gpt-5-nano` | Model for Q&A |

## Building the Image

### Build Locally

```bash
docker build -t crl.help .
```

### Build for Multiple Platforms

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t crl.help:latest .
```

## GitHub Container Registry

Images are automatically built and pushed to GitHub Container Registry on every push to `main`.

### Pull from GHCR

```bash
docker pull ghcr.io/armish/crl.help:latest
```

### Available Tags

- `latest` - Latest build from main branch
- `main` - Same as latest
- `v1.0.0` - Semantic version tags
- `sha-abc1234` - Git commit SHA tags

## Docker Compose Examples

### Basic Setup

```yaml
version: '3.8'

services:
  web:
    image: ghcr.io/armish/crl.help:latest
    ports:
      - "80:80"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./backend/data:/app/backend/data
```

### Production Setup with Nginx Proxy

```yaml
version: '3.8'

services:
  crl-help:
    image: ghcr.io/armish/crl.help:latest
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - LOG_LEVEL=WARNING
      - CORS_ORIGINS=https://crl.help
    volumes:
      - crl-data:/app/backend/data
    restart: unless-stopped

  nginx-proxy:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx-proxy.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - crl-help
    restart: unless-stopped

volumes:
  crl-data:
```

## Health Checks

The container includes a health check that verifies:
- Nginx is running
- Backend API is responding
- Database is accessible

View health status:

```bash
docker ps  # Check STATUS column
docker inspect --format='{{json .State.Health}}' <container-id>
```

## Logs

View logs from both services:

```bash
# All logs
docker-compose logs -f

# Backend only
docker-compose logs -f web | grep backend

# Nginx only
docker-compose logs -f web | grep nginx
```

## Troubleshooting

### Database Download Fails

If the database fails to download:

1. Check the DATABASE_URL is accessible
2. Verify network connectivity from container
3. Check disk space: `docker system df`
4. View logs: `docker-compose logs web`

### Application Won't Start

1. Check if required environment variables are set:
```bash
docker-compose exec web env | grep -E 'DATABASE|OPENAI'
```

2. Verify database exists:
```bash
docker-compose exec web ls -lh /app/backend/data/
```

3. Check backend logs:
```bash
docker-compose logs web | grep "FastAPI"
```

### Port 80 Already in Use

Change the port mapping in docker-compose.yml:

```yaml
ports:
  - "8080:80"  # Use port 8080 instead
```

Then access at http://localhost:8080

## Performance Tuning

### Resource Limits

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Caching

The Dockerfile uses multi-stage builds and layer caching for faster builds:

```bash
# Rebuild with cache
docker-compose build

# Force rebuild without cache
docker-compose build --no-cache
```

## Security

### Running as Non-Root

The backend service runs as user `appuser` (UID 1000) for security.

### Read-Only Database

Mount database as read-only if you don't need to modify it:

```yaml
volumes:
  - ./crl_explorer.duckdb:/app/backend/data/crl_explorer.duckdb:ro
```

### Environment Variables

**Never commit .env files to Git!** Use secrets management in production:

```bash
# GitHub Actions
- name: Deploy
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Updating

### Pull Latest Image

```bash
docker-compose pull
docker-compose up -d
```

### Automatic Updates with Watchtower

```yaml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 300 --cleanup
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/armish/crl.help/issues
- Documentation: https://github.com/armish/crl.help
