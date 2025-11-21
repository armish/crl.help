# Automated Data Updates

This document describes how the CRL Explorer automatically updates its database when FDA data changes.

## Overview

A GitHub Actions workflow runs daily to check if FDA data has changed. If changes are detected, it:
1. Downloads fresh FDA data
2. Runs the complete AI processing pipeline (~30 minutes)
3. Uploads the new database to GitHub Releases

## Components

### `backend/check_for_updates.py` - Change Detection Script

Downloads FDA bulk data and computes SHA256 hash, then compares with previously stored hash.

**Exit codes:**
- `0` - Data has changed (or first run), pipeline should run
- `1` - No changes detected, pipeline can be skipped
- `2` - Error occurred

**Usage:**
```bash
# Check for updates
python check_for_updates.py

# Store hash after successful pipeline run
python check_for_updates.py --store-hash

# Force "changed" status (for testing)
python check_for_updates.py --force
```

### `backend/ingest_data_ci.py` - Non-Interactive Pipeline

CI/CD-friendly version of `ingest_data.py`. No prompts, no confirmations.

**Pipeline steps:**
1. Load CRL data from openFDA API
2. Generate AI summaries
3. Extract product indications
4. Extract product names
5. Classify deficiency reasons
6. Classify therapeutic categories
7. Set last update timestamp

**Usage:**
```bash
python ingest_data_ci.py
```

### `.github/workflows/update-data.yml` - GitHub Actions Workflow

- **Schedule:** Daily at 2 AM UTC
- **Manual trigger:** Available with optional "force update" checkbox
- **Output:** GitHub Release with database file

## Setup

### 1. Add GitHub Secret

Add your OpenAI API key as a repository secret:

1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `OPENAI_API_KEY`
5. Value: Your OpenAI API key (starts with `sk-`)

### 2. First Run (Recommended)

Manually trigger the workflow to create the initial database:

1. Go to Actions → "Update CRL Data"
2. Click "Run workflow"
3. Check "Force update even if no changes detected"
4. Click "Run workflow"

This will take ~30 minutes and create the first release.

## How It Works

```
Daily at 2 AM UTC
       │
       ▼
┌─────────────────────┐
│ check_for_updates.py│
│ (compare hash)      │
└─────────────────────┘
       │
       ├── No change → Skip (exit 1)
       │
       ▼ Changed (exit 0)
┌─────────────────────┐
│ ingest_data_ci.py   │
│ (full pipeline)     │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ GitHub Release      │
│ data-YYYY-MM-DD     │
│ crl_explorer.duckdb │
└─────────────────────┘
```

## Using the Database

### Download Latest Database

```bash
# List available releases
gh release list --repo armish/crl.help

# Download specific release
gh release download data-2025-01-15 --pattern "*.duckdb" --repo armish/crl.help

# Or download directly via URL
wget https://github.com/armish/crl.help/releases/download/data-2025-01-15/crl_explorer.duckdb
```

### Use with Docker

```bash
docker run -d -p 80:80 \
  -e DATABASE_URL=https://github.com/armish/crl.help/releases/download/data-2025-01-15/crl_explorer.duckdb \
  ghcr.io/armish/crl.help:latest
```

### Use Locally

```bash
# Copy to backend data directory
cp crl_explorer.duckdb backend/data/

# Start the server
cd backend
python -m uvicorn app.main:app --reload
```

## Monitoring

### Check Workflow Runs

1. Go to Actions → "Update CRL Data"
2. View run history and logs
3. Each run shows a summary indicating if data was updated

### Release History

All database versions are preserved as GitHub Releases:
- Tagged as `data-YYYY-MM-DD`
- Include download instructions in release notes
- Can roll back to any previous version if needed

## Troubleshooting

### Workflow Fails at "Check for FDA data updates"

- Ensure the FDA API is accessible
- Check if the URL has changed: `https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip`

### Workflow Fails at "Run data ingestion pipeline"

- Verify `OPENAI_API_KEY` secret is set correctly
- Check OpenAI API quota/billing
- Review logs for specific error messages

### Database Not Created

- Check that all pipeline steps completed successfully
- Verify disk space on GitHub Actions runner
- Review `ingest_data_ci.py` logs for errors

## Cost Considerations

- **GitHub Actions:** Free for public repositories (2,000 minutes/month for private)
- **OpenAI API:** ~$0.10 per full pipeline run (summarization + classification)
- **Storage:** GitHub Releases are free for public repositories

Since FDA data changes infrequently (typically weekly or less), the actual cost is minimal.
