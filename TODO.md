# FDA CRL Explorer - Current State & Future Plans

## Project Overview

A full-stack Python application for exploring FDA Complete Response Letters with AI-powered summarization.

The webapp is in a really great place! This document focuses on realistic, achievable goals.

---

## Technology Stack

### Backend
- **Framework**: FastAPI (async, modern, auto-generated API docs)
- **Database**: DuckDB (embedded, excellent JSON support, analytics-optimized, no separate server needed)
- **AI Services**: OpenAI API (GPT-4o-mini for summarization)
- **Data Processing**: pandas (data manipulation), httpx (async HTTP client)

### Frontend
- **Framework**: React + Vite (fast, modern, component-based)
- **UI Library**: Tailwind CSS + shadcn/ui (beautiful, accessible components)
- **Data Fetching**: TanStack Query (React Query v5 - caching, background updates)
- **Table Component**: TanStack Table (powerful filtering, sorting, pagination)
- **State Management**: Zustand (lightweight, simple)

### Why This Stack?
- **DuckDB**: Perfect for this use case - handles JSON natively, fast analytics queries, embedded (no server)
- **FastAPI**: Modern async Python framework, auto-generated OpenAPI docs, excellent validation with Pydantic
- **Small scale**: ~400 records, simple and efficient
- **Cost-effective**: No separate database server, minimal infrastructure

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  Table   │  │  Filters │  │  Detail  │                 │
│  │  View    │  │    UI    │  │  Modal   │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/JSON
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  Backend API (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  REST Endpoints: /crls, /stats                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌────────────────┬────────┴────────────────────────────┐  │
│  │  Data          │  AI Services                        │  │
│  │  Ingestion     │  - Summarization                    │  │
│  │  Service       │                                     │  │
│  └────────────────┴─────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    DuckDB Database                           │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ crls        │  │ crl_         │  │ metadata         │  │
│  │ (raw data)  │  │ summaries    │  │ (job status)     │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    External Services                         │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │ FDA API          │  │ OpenAI API                     │  │
│  │ (bulk download)  │  │ (summarization)                │  │
│  └──────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Table: `crls`
Stores raw CRL data from FDA API.

```sql
CREATE TABLE crls (
    id VARCHAR PRIMARY KEY,                    -- Generated from application_number + letter_date
    application_number VARCHAR[],              -- e.g., ["NDA 215818"]
    letter_date DATE,                          -- Parsed from MM/DD/YYYY
    letter_year VARCHAR,
    letter_type VARCHAR,                       -- "COMPLETE RESPONSE"
    approval_status VARCHAR,                   -- "Approved" or "Unapproved"
    company_name VARCHAR,
    company_address VARCHAR,
    company_rep VARCHAR,
    approver_name VARCHAR,
    approver_center VARCHAR[],                 -- e.g., ["Center for Drug Evaluation and Research"]
    approver_title VARCHAR,
    file_name VARCHAR,
    text TEXT,                                 -- Full letter content
    raw_json JSON,                             -- Original JSON for reference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: `crl_summaries`
Stores AI-generated summaries.

```sql
CREATE TABLE crl_summaries (
    id VARCHAR PRIMARY KEY,
    crl_id VARCHAR REFERENCES crls(id),
    summary TEXT,                              -- AI-generated paragraph summary
    model VARCHAR,                             -- e.g., "gpt-4o-mini"
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER
);
```


### Table: `processing_metadata`
Tracks processing status.

```sql
CREATE TABLE processing_metadata (
    key VARCHAR PRIMARY KEY,
    value VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Examples: last_download_date, last_processing_date, total_crls_processed
```

---

## Project Structure

```
crl-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── config.py                  # Configuration (env vars, settings)
│   │   ├── database.py                # DuckDB connection & initialization
│   │   ├── models.py                  # Pydantic models (request/response)
│   │   ├── schemas.py                 # Database schemas (SQL)
│   │   │
│   │   ├── api/                       # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── crls.py                # CRL CRUD endpoints
│   │   │   ├── stats.py               # Statistics endpoints
│   │   │   ├── qa.py                  # Q&A endpoints
│   │   │   └── export.py              # Export endpoints
│   │   │
│   │   ├── services/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── data_ingestion.py      # Download & parse FDA data
│   │   │   ├── data_processor.py      # Process & store CRLs
│   │   │   ├── summarization.py       # OpenAI summarization
│   │   │   ├── embeddings.py          # OpenAI embeddings generation
│   │   │   ├── rag.py                 # RAG: retrieval + generation
│   │   │   └── export_service.py      # Export to CSV/Excel
│   │   │
│   │   ├── tasks/                     # Scheduled tasks
│   │   │   ├── __init__.py
│   │   │   └── scheduler.py           # APScheduler setup & jobs
│   │   │
│   │   └── utils/                     # Utilities
│   │       ├── __init__.py
│   │       ├── openai_client.py       # OpenAI API wrapper
│   │       ├── vector_utils.py        # Vector similarity functions
│   │       └── logging_config.py      # Logging setup
│   │
│   ├── data/                          # Local data directory
│   │   ├── raw/                       # Downloaded bulk data
│   │   ├── processed/                 # Processed data
│   │   └── crl_explorer.duckdb        # DuckDB database file
│   │
│   ├── tests/                         # Backend tests
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_services.py
│   │   └── test_rag.py
│   │
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Example environment variables
│   └── README.md                      # Backend documentation
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CRLTable.jsx           # Main table component
│   │   │   ├── FilterPanel.jsx        # Search & filter UI
│   │   │   ├── CRLDetailModal.jsx     # Detail view modal
│   │   │   ├── QAPanel.jsx            # Q&A interface
│   │   │   ├── StatsCards.jsx         # Summary statistics
│   │   │   └── ExportButton.jsx       # Export functionality
│   │   │
│   │   ├── services/
│   │   │   ├── api.js                 # API client
│   │   │   └── queries.js             # React Query hooks
│   │   │
│   │   ├── store/
│   │   │   └── filterStore.js         # Zustand store for filters
│   │   │
│   │   ├── pages/
│   │   │   ├── HomePage.jsx           # Main application page
│   │   │   └── AboutPage.jsx          # About/documentation
│   │   │
│   │   ├── App.jsx                    # Root component
│   │   ├── main.jsx                   # Entry point
│   │   └── index.css                  # Global styles
│   │
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── README.md
│
├── .gitignore
├── FDA_CRL_API.md                     # API documentation (created)
├── TODO.md                            # This file
└── README.md                          # Project overview
```

---

## Implementation Plan

### Phase 1: Foundation & Setup

#### 1.1 Project Initialization ✅ COMPLETED
- [x] Create project directory structure
- [x] Initialize Git repository
- [x] Set up `.gitignore` (exclude `.env`, `data/`, `*.duckdb`, `node_modules/`)
- [x] Create backend virtual environment
- [x] Create `requirements.txt` with initial dependencies
- [x] Create `.env.example` template
- [ ] Initialize frontend with Vite + React

**Dependencies (requirements.txt):**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
duckdb==0.9.2
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
httpx==0.25.1
pandas==2.1.3
openai==1.3.5
apscheduler==3.10.4
python-multipart==0.0.6
openpyxl==3.1.2
numpy==1.26.2
```

#### 1.2 Configuration Management ✅ COMPLETED
- [x] Create `app/config.py` with Pydantic Settings
- [x] Define environment variables:
  - `OPENAI_API_KEY` (required, never exposed to frontend)
  - `DATABASE_PATH` (default: `./data/crl_explorer.duckdb`)
  - `FDA_BULK_APPROVED_URL`
  - `FDA_BULK_UNAPPROVED_URL`
  - `SCHEDULE_HOUR` (default: 2 AM)
  - `LOG_LEVEL` (default: INFO)
  - `CORS_ORIGINS` (allowed frontend origins)
- [x] Add validation for required environment variables
- [x] Create `.env.example` with placeholder values

#### 1.3 Logging Setup ✅ COMPLETED
- [x] Create `app/utils/logging_config.py`
- [x] Configure structured logging (JSON format)
- [x] Set up file rotation
- [x] Add request ID tracking for API calls

---

### Phase 2: Database Layer ✅ COMPLETED

#### 2.1 Database Setup ✅ COMPLETED
- [x] Create `app/database.py` with DuckDB connection manager
- [x] Implement connection pooling/singleton pattern
- [x] Create `app/schemas.py` with all table definitions (SQL)
- [x] Write database initialization function (`init_db()`)
- [x] Create indexes for common queries:
  - `approval_status`
  - `letter_year`
  - `company_name`
  - `letter_date`

#### 2.2 Data Access Layer ✅ COMPLETED
- [x] Create repository pattern classes in `app/database.py`:
  - `CRLRepository` (CRUD operations for CRLs)
  - `SummaryRepository`
  - `EmbeddingRepository`
  - `QARepository`
- [x] Implement query builders for filtering/sorting
- [x] Add pagination support
- [x] Write helper functions for vector similarity search

#### 2.3 Database Testing
- [ ] Create test database setup
- [ ] Write unit tests for repositories
- [ ] Test data insertion and retrieval
- [ ] Verify index performance

---

### Phase 2.5: Testing Infrastructure Setup

#### 2.5.1 Test Framework Setup
- [ ] Install pytest and pytest-cov
- [ ] Create pytest.ini configuration file
- [ ] Set up test directory structure
- [ ] Configure coverage reporting (HTML, terminal, and XML)
- [ ] Add pytest-asyncio for async test support
- [ ] Add pytest-mock for mocking support

#### 2.5.2 Code Coverage Configuration
- [ ] Set up .coveragerc configuration
- [ ] Configure minimum coverage thresholds
- [ ] Set up coverage reports in CI/CD (future)
- [ ] Add coverage badges to README (future)

#### 2.5.3 Initial Unit Tests
- [ ] Write tests for `app/config.py` (settings validation)
- [ ] Write tests for `app/utils/logging_config.py`
- [ ] Write tests for `app/database.py` (connection management)
- [ ] Write tests for `app/schemas.py` (table creation)
- [ ] Achieve >80% coverage for core modules

#### 2.5.4 Test Utilities
- [ ] Create test fixtures for database connections
- [ ] Create mock factories for test data
- [ ] Set up test database (in-memory or temporary)
- [ ] Create helper functions for common test scenarios

**Testing Dependencies to Add:**
```
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
pytest-mock==3.12.0
coverage[toml]==7.3.2
```

---

### Phase 3: Data Ingestion Pipeline ✅ COMPLETED

#### 3.1 Download Service ✅ COMPLETED
- [x] Create `app/services/data_ingestion.py`
- [x] Implement `download_bulk_data()` function:
  - Download CRL JSON ZIP file from FDA
  - Extract JSON files
  - Validate downloads
- [x] Add retry logic with exponential backoff (using tenacity)
- [x] Implement progress logging
- [x] Store raw files in `data/raw/`

#### 3.2 Data Processing ✅ COMPLETED
- [x] Create `app/services/data_processor.py`
- [x] Implement `parse_crl_data()` function:
  - Parse JSON structure
  - Validate required fields
  - Transform dates (MM/DD/YYYY and YYYYMMDD → YYYY-MM-DD)
  - Generate unique CRL IDs
- [x] Implement `detect_new_crls()` function:
  - Compare with existing database
  - Identify new records
  - Identify updated records
- [x] Implement `store_crls()` function:
  - Bulk insert new CRLs
  - Update existing CRLs if changed
  - Track metadata (last_download_date)

#### 3.3 Testing ✅ COMPLETED
- [x] Create sample CRL data for testing (47 comprehensive tests)
- [x] Test download error handling (network errors, timeouts, retry logic)
- [x] Test duplicate detection (ID collision resolution with hashing)
- [x] Verify data integrity after processing (date parsing, edge cases)
- [x] Test all Phase 3 services with 100% test pass rate

---

### Phase 4: AI Services ✅ COMPLETED

#### 4.1 OpenAI Client ✅ COMPLETED
- [x] Create `app/utils/openai_client.py`
- [x] Implement wrapper class with:
  - API key management (from config)
  - Rate limiting (exponential backoff via OpenAI client)
  - Error handling and retries
  - Token usage tracking
  - Timeout configuration
- [x] Add logging for all API calls
- [x] Implement cost estimation

#### 4.2 Summarization Service ✅ COMPLETED
- [x] Create `app/services/summarization.py`
- [x] Design prompt template focused on deficiencies and key points
- [x] Implement `summarize_crl(text)` function:
  - Call GPT-4o-mini API
  - Extract summary from response
  - Track tokens used
- [x] Implement batch processing with progress tracking
- [x] Add retry logic for failures (via OpenAI client)
- [x] Created CLI script `generate_summaries.py` for batch processing

#### 4.3 Embedding Service ✅ COMPLETED
- [x] Create `app/services/embeddings.py`
- [x] Implement `generate_embedding(text)` function:
  - Use `text-embedding-3-small` (1536 dimensions)
  - Handle text truncation (max 8191 tokens)
  - Return numpy array
- [x] Implement batch embedding generation
- [x] Create embeddings for summaries
- [x] Normalize vectors for cosine similarity
- [x] Created CLI script `generate_embeddings.py` for batch processing

#### 4.4 Testing ✅ COMPLETED
- [x] Test summarization with sample CRLs (dry-run mode)
- [x] Verify embedding dimensions
- [x] Test batch processing
- [x] Validate error handling and retries
- [x] Monitor token usage and costs
- [x] 23 comprehensive tests covering all AI services

---

### Phase 7: Backend API (FastAPI) ✅ COMPLETED

#### 7.1 Main Application ✅ COMPLETED
- [x] Create `app/main.py` with FastAPI app
- [x] Configure CORS (restrict to frontend origin)
- [x] Add health check endpoint: `GET /health` with database stats
- [x] Include API routers
- [x] Add startup event to initialize database
- [x] Configure exception handlers (404, 500)
- [x] Add lifespan context manager for startup/shutdown
- [x] Auto-generated OpenAPI documentation at `/docs`

#### 7.2 Pydantic Models ✅ COMPLETED
- [x] Create `app/models.py` with request/response models:
  - `CRLListItem` (list view)
  - `CRLWithSummary` (detail view with AI summary)
  - `CRLWithText` (full text view)
  - `CRLListResponse` (paginated list)
  - `StatsOverview` (statistics)
  - `CompanyStats` (company statistics)
  - `QARequest` (question with validation)
  - `QAResponse` (answer with citations)
  - `QAHistoryItem` and `QAHistoryResponse`
  - `HealthResponse` (health check)

#### 7.3 CRL Endpoints ✅ COMPLETED
- [x] Create `app/api/crls.py`
- [x] Implement endpoints:
  - `GET /api/crls` - List CRLs with filtering, sorting, pagination
    - Query params: approval_status, letter_year, company_name, search_text, limit (1-100), offset, sort_by, sort_order
    - Return: paginated list with total count and has_more flag
  - `GET /api/crls/{crl_id}` - Get single CRL with summary
    - Return: full CRL metadata + AI summary
  - `GET /api/crls/{crl_id}/text` - Get full letter text
    - Return: CRL with complete letter text

#### 7.4 Statistics Endpoints ✅ COMPLETED
- [x] Create `app/api/stats.py`
- [x] Implement endpoints:
  - `GET /api/stats/overview` - Overall statistics
    - Total CRLs, by_status breakdown, by_year breakdown
  - `GET /api/stats/companies` - Top companies by CRL count
    - Sorted by CRL count with approved/unapproved breakdown


#### 7.6 Export Endpoints
- [ ] Create `app/api/export.py` (deferred - not MVP critical)
- [ ] Create `app/services/export_service.py`
- [ ] Implement CSV/Excel export functionality

#### 7.7 Testing ✅ COMPLETED
- [x] Write API tests for all endpoints (comprehensive tests)
- [x] Test filtering and pagination
- [x] Test error responses (404, 400, 422, 500)
- [x] Test CORS configuration
- [x] Test health check with database stats
- [x] Test API documentation accessibility
- [x] Tests use in-memory database with mock data

---

## Current State - What's Working Great! ✅

### Backend ✅ COMPLETED
- [x] FastAPI application with health checks
- [x] DuckDB database with optimized schema
- [x] Data ingestion pipeline from FDA API
- [x] AI-powered summarization service
- [x] REST API endpoints for CRLs and statistics
- [x] Comprehensive test coverage
- [x] Docker deployment setup

### Frontend ✅ COMPLETED
- [x] React + Vite application
- [x] Beautiful UI with Tailwind CSS + shadcn/ui
- [x] Interactive CRL table with filtering and sorting
- [x] Detail modal with AI summaries
- [x] Statistics dashboard
- [x] Responsive design
- [x] Production deployment ready

---

## Automated Data Updates ✅ IMPLEMENTED

### How It Works

A GitHub Actions workflow runs daily to check if FDA data has changed. If changes are detected, it:
1. Downloads fresh FDA data
2. Runs the complete AI processing pipeline
3. Uploads the new database to GitHub Releases

### Components

**`backend/check_for_updates.py`** - Change Detection Script
- Downloads FDA bulk data and computes SHA256 hash
- Compares with previously stored hash in database
- Exit code 0 = data changed, exit code 1 = no change

**`backend/ingest_data_ci.py`** - Non-Interactive Pipeline
- CI/CD-friendly version of `ingest_data.py`
- No prompts, no confirmations
- Runs all 7 pipeline steps automatically

**`.github/workflows/update-data.yml`** - GitHub Actions Workflow
- Runs daily at 2 AM UTC
- Checks for FDA data changes
- If changed: runs pipeline and creates new GitHub Release
- Database uploaded to: `https://github.com/{repo}/releases/download/data-{date}/crl_explorer.duckdb`

### Setup Required

1. **Add GitHub Secret**: `OPENAI_API_KEY`
   - Go to repo Settings → Secrets and variables → Actions
   - Add new secret named `OPENAI_API_KEY`

2. **Manual Trigger** (optional):
   - Go to Actions → "Update CRL Data" → Run workflow
   - Check "Force update" to bypass change detection

### Usage

**Download latest database:**
```bash
# Find latest release
gh release list --repo armish/crl.help

# Download database
gh release download data-2025-01-15 --pattern "*.duckdb" --repo armish/crl.help
```

**Use with Docker:**
```bash
docker run -d -p 80:80 \
  -e DATABASE_URL=https://github.com/armish/crl.help/releases/download/data-2025-01-15/crl_explorer.duckdb \
  ghcr.io/armish/crl.help:latest
```

---

## Security Checklist ✅

- [x] OpenAI API key stored in environment variable
- [x] API key never exposed to frontend
- [x] API key never logged
- [x] .env file in .gitignore
- [x] Pre-commit hook to prevent accidental secret exposure
- [x] CORS restricted to specific origins
- [x] All user inputs validated
- [x] HTTPS in production (via hosting platform)
- [x] No hardcoded secrets in code

---

## Key Design Decisions

### Why DuckDB?
- **Perfect for analytics**: Optimized for read-heavy workloads
- **Embedded**: No separate database server needed
- **JSON support**: Native JSON columns for raw data storage
- **Small footprint**: Perfect for ~400 records
- **Serverless-friendly**: Single file database, easy backups

### Summarization Approach
- Single paragraph (3-5 sentences)
- Focus on deficiencies, not boilerplate
- GPT-4o-mini for cost efficiency
- Cache summaries to avoid re-processing

### Data Update Strategy (Current)
- Manual bulk download when needed
- Full re-ingestion is fast (~5 minutes)
- Simple and reliable
- Automate only if data changes frequently

---

## Cost Estimation

### OpenAI API Costs (~400 CRLs)

**Summarization (GPT-4o-mini):**
- Total cost for initial setup: < $0.10
- Ongoing costs: Minimal (few new CRLs per week/month)

**Note:** Very cost-effective due to small dataset size.
