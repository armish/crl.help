# FDA CRL Explorer - Implementation Plan

## Project Overview

A full-stack Python application for mining and exploring FDA Complete Response Letters with AI-powered summarization, semantic search, and interactive Q&A capabilities.

---

## Technology Stack

### Backend
- **Framework**: FastAPI (async, modern, auto-generated API docs)
- **Database**: DuckDB (embedded, excellent JSON support, analytics-optimized, no separate server needed)
- **AI Services**: OpenAI API (GPT-4o-mini for summarization, text-embedding-3-small for embeddings)
- **Task Scheduling**: APScheduler (lightweight, in-process scheduler)
- **Data Processing**: pandas (data manipulation), httpx (async HTTP client)

### Frontend
- **Framework**: React + Vite (fast, modern, component-based)
- **UI Library**: Tailwind CSS + shadcn/ui (beautiful, accessible components)
- **Data Fetching**: TanStack Query (React Query v5 - caching, background updates)
- **Table Component**: TanStack Table (powerful filtering, sorting, pagination)
- **State Management**: Zustand (lightweight, simple)

### Why This Stack?
- **DuckDB**: Perfect for this use case - handles JSON natively, fast analytics queries, embedded (no server), supports vector similarity search via extensions
- **FastAPI**: Modern async Python framework, auto-generated OpenAPI docs, excellent validation with Pydantic
- **Small scale**: 392 records currently, but architecture scales to millions with DuckDB
- **RAG-ready**: DuckDB can handle vector similarity with vss extension, or we can use simple cosine similarity
- **Cost-effective**: No separate database server, minimal infrastructure

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Table   │  │  Filters │  │  Detail  │  │   Q&A    │   │
│  │  View    │  │    UI    │  │  Modal   │  │  Panel   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/JSON
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  Backend API (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  REST Endpoints: /crls, /stats, /qa, /export        │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌────────────────┬────────┴────────┬──────────────────┐   │
│  │  Data          │  AI Services    │  RAG Engine      │   │
│  │  Ingestion     │  - Summarize    │  - Embed Search  │   │
│  │  Service       │  - Embeddings   │  - Q&A           │   │
│  └────────────────┴─────────────────┴──────────────────┘   │
│                            │                                 │
│  ┌────────────────────────▼─────────────────────────────┐  │
│  │         APScheduler (Daily Tasks)                    │  │
│  │  - Download bulk data                                │  │
│  │  - Process new CRLs                                  │  │
│  │  - Generate summaries & embeddings                   │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    DuckDB Database                           │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ crls        │  │ crl_         │  │ crl_embeddings   │  │
│  │ (raw data)  │  │ summaries    │  │ (vectors)        │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐                         │
│  │ qa_         │  │ metadata     │                         │
│  │ annotations │  │ (job status) │                         │
│  └─────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    External Services                         │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │ FDA API          │  │ OpenAI API                     │  │
│  │ (bulk download)  │  │ (summarization & embeddings)   │  │
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

### Table: `crl_embeddings`
Stores vector embeddings for RAG.

```sql
CREATE TABLE crl_embeddings (
    id VARCHAR PRIMARY KEY,
    crl_id VARCHAR REFERENCES crls(id),
    embedding_type VARCHAR,                    -- "summary" or "full_text"
    embedding FLOAT[],                         -- Vector (1536 dimensions for text-embedding-3-small)
    model VARCHAR,                             -- e.g., "text-embedding-3-small"
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: `qa_annotations`
Stores user questions and AI answers.

```sql
CREATE TABLE qa_annotations (
    id VARCHAR PRIMARY KEY,
    question TEXT,
    answer TEXT,
    relevant_crl_ids VARCHAR[],                -- CRLs used to answer
    model VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

### Phase 5: RAG Implementation ✅ COMPLETED

#### 5.1 Vector Search ✅ COMPLETED
- [x] Create `app/utils/vector_utils.py`
- [x] Implement cosine similarity function with optimizations
- [x] Implement `find_top_k_similar()` function:
  - Query all embeddings from database
  - Calculate similarity scores using various metrics
  - Return top-k CRL IDs with scores
  - Support for cosine, euclidean, dot product similarities
- [x] Comprehensive vector utilities (normalize, magnitude, mean, etc.)
- [x] 52 comprehensive tests for all vector operations

#### 5.2 RAG Service ✅ COMPLETED
- [x] Create `app/services/rag.py`
- [x] Implement `answer_question(question: str)` function:
  1. Generate embedding for question
  2. Retrieve top-k relevant CRLs (k=5, configurable)
  3. Construct context from retrieved CRLs
  4. Build prompt for GPT-4o-mini with FDA expertise
  5. Call OpenAI API
  6. Store Q&A in `qa_annotations` table
  7. Return answer with cited CRL IDs
- [x] Add fallback for no relevant CRLs found
- [x] Implement confidence scoring based on similarity
- [x] Created CLI script `ask_question.py` for interactive Q&A

#### 5.3 Testing ✅ COMPLETED
- [x] Test with sample questions (dry-run mode)
- [x] Verify retrieval accuracy
- [x] Test edge cases (no relevant CRLs, empty questions)
- [x] Evaluate answer quality
- [x] Test confidence computation
- [x] Test Q&A history storage and retrieval

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

#### 7.5 Q&A Endpoints ✅ COMPLETED
- [x] Create `app/api/qa.py`
- [x] Implement endpoints:
  - `POST /api/qa/ask` - Submit question (RAG-powered)
    - Request: `{ "question": "...", "top_k": 5 }`
    - Response: `{ "answer": "...", "relevant_crls": [...], "confidence": 0.85, "model": "..." }`
  - `GET /api/qa/history` - Get past Q&A with pagination

#### 7.6 Export Endpoints
- [ ] Create `app/api/export.py` (deferred - not MVP critical)
- [ ] Create `app/services/export_service.py`
- [ ] Implement CSV/Excel export functionality

#### 7.7 Testing ✅ COMPLETED
- [x] Write API tests for all endpoints (26 comprehensive tests)
- [x] Test filtering and pagination
- [x] Test error responses (404, 400, 422, 500)
- [x] Test CORS configuration
- [x] Test health check with database stats
- [x] Test Q&A with mocked RAG service
- [x] Test API documentation accessibility
- [x] All 26 tests passing in CI/CD environment
- [x] Tests use in-memory database with mock data

---

### Phase 6: Scheduled Tasks (DEFERRED - After MVP)

**Note**: As discussed, we're deferring scheduled tasks to avoid over-engineering. The priority is getting a working tool first, then adding automation later.

#### 6.1 Scheduler Setup
- [ ] Create `app/tasks/scheduler.py`
- [ ] Configure APScheduler with BackgroundScheduler
- [ ] Add shutdown hooks for graceful termination

#### 6.2 Daily Data Pipeline Job
- [ ] Create `daily_data_pipeline()` function:
  1. Download bulk data
  2. Parse and detect new CRLs
  3. Store new CRLs in database
  4. Generate summaries for new CRLs
  5. Generate embeddings for new summaries
  6. Update processing metadata
  7. Log summary (X new CRLs processed)
- [ ] Schedule to run at configured time (default: 2 AM)
- [ ] Add error notifications (log errors prominently)
- [ ] Implement idempotency (safe to run multiple times)

#### 6.3 Initial Data Load
- [x] CLI scripts created for manual execution:
  - `load_data.py` - Download and process CRLs
  - `generate_summaries.py` - Batch summarization
  - `generate_embeddings.py` - Batch embedding generation
  - `ask_question.py` - Interactive Q&A
- [ ] Convert to scheduled automation (future enhancement)

#### 6.4 Testing
- [ ] Test scheduler starts correctly
- [ ] Verify job runs on schedule
- [ ] Test error handling
- [ ] Ensure no duplicate processing

---

### Phase 8: Frontend - Foundation

#### 8.1 Project Setup
- [ ] Initialize Vite + React project: `npm create vite@latest frontend -- --template react`
- [ ] Install dependencies:
  ```bash
  npm install @tanstack/react-query @tanstack/react-table
  npm install zustand axios
  npm install tailwindcss postcss autoprefixer
  npm install @headlessui/react @heroicons/react
  npm install react-router-dom
  ```
- [ ] Install shadcn/ui components: `npx shadcn-ui@latest init`
- [ ] Configure Tailwind CSS
- [ ] Set up proxy for API calls in `vite.config.js`

#### 8.2 API Client
- [ ] Create `src/services/api.js`:
  - Axios instance with base URL
  - Error interceptors
  - Request/response logging
- [ ] Create `src/services/queries.js`:
  - React Query hooks for all endpoints
  - `useСRLs()` - fetch CRLs with filters
  - `useCRL(id)` - fetch single CRL
  - `useStats()` - fetch statistics
  - `useAskQuestion()` - mutation for Q&A
  - `useExport()` - trigger export

#### 8.3 State Management
- [ ] Create `src/store/filterStore.js` with Zustand:
  - Filter state (approval_status, year, company, search text)
  - Sort state
  - Pagination state
  - Actions to update filters

#### 8.4 Layout
- [ ] Create main layout component with:
  - Header (app title, navigation)
  - Sidebar (filter panel)
  - Main content area
  - Footer (credits, links to FDA docs)

---

### Phase 9: Frontend - Core Features

#### 9.1 Statistics Dashboard
- [ ] Create `src/components/StatsCards.jsx`:
  - Total CRLs card
  - Approved/Unapproved breakdown
  - Chart showing CRLs by year (bar chart)
  - Top companies (pie chart or list)
- [ ] Use Chart.js or Recharts for visualizations

#### 9.2 Filter Panel
- [ ] Create `src/components/FilterPanel.jsx`:
  - Search input (full-text search)
  - Approval status dropdown/radio buttons
  - Year multi-select
  - Company autocomplete/select
  - FDA Center multi-select
  - Clear filters button
- [ ] Connect to filterStore
- [ ] Debounce search input

#### 9.3 CRL Table
- [ ] Create `src/components/CRLTable.jsx` using TanStack Table:
  - Columns: Application #, Company, Date, Year, Status, FDA Center
  - Row click to open detail modal
  - Sortable columns
  - Loading states
  - Empty state
- [ ] Implement virtualization if needed (react-virtual)
- [ ] Add pagination controls
- [ ] Highlight search matches

#### 9.4 Detail Modal
- [ ] Create `src/components/CRLDetailModal.jsx`:
  - Modal overlay (Headless UI Dialog)
  - Display all CRL metadata
  - Show AI-generated summary prominently
  - Full letter text (collapsible or tabbed)
  - Download PDF button (if file_name available)
  - Close button
- [ ] Responsive design for mobile

#### 9.5 Q&A Panel
- [ ] Create `src/components/QAPanel.jsx`:
  - Question input textarea
  - Submit button
  - Loading state while processing
  - Display answer with formatting
  - Show cited CRLs (clickable to open modal)
  - Q&A history list (optional)
- [ ] Add character limit warning
- [ ] Show token usage/cost estimate

#### 9.6 Export Functionality
- [ ] Create `src/components/ExportButton.jsx`:
  - Dropdown menu: Export CSV / Export Excel
  - Checkbox: Include summaries
  - Checkbox: Include current filters only
  - Trigger download
- [ ] Handle loading state
- [ ] Show success notification

---

### Phase 10: Frontend - Polish & UX

#### 10.1 Error Handling
- [ ] Create error boundary component
- [ ] Display user-friendly error messages
- [ ] Add retry buttons for failed requests
- [ ] Toast notifications for success/error (react-hot-toast)

#### 10.2 Loading States
- [ ] Skeleton loaders for table
- [ ] Spinners for API calls
- [ ] Progress indicators for Q&A processing
- [ ] Optimistic updates where appropriate

#### 10.3 Responsive Design
- [ ] Mobile-friendly table (cards on small screens)
- [ ] Responsive filter panel (drawer on mobile)
- [ ] Touch-friendly interactions
- [ ] Test on multiple screen sizes

#### 10.4 Accessibility
- [ ] Keyboard navigation
- [ ] ARIA labels
- [ ] Focus management (modals, dropdowns)
- [ ] Screen reader testing

#### 10.5 Performance
- [ ] Code splitting (React.lazy)
- [ ] Memoization (React.memo, useMemo)
- [ ] Virtual scrolling for large lists
- [ ] Image optimization (if any)

---

### Phase 11: Security & Configuration

#### 11.1 Environment Variables
- [ ] Backend: Validate all required env vars on startup
- [ ] Frontend: Create `.env` for API URL (no secrets!)
- [ ] Document all environment variables in README

#### 11.2 API Key Security
- [ ] Verify API key is ONLY in backend
- [ ] Never log API keys
- [ ] Use environment variables (not hardcoded)
- [ ] Add .env to .gitignore

#### 11.3 CORS Configuration
- [ ] Restrict CORS to specific frontend origin(s)
- [ ] Test cross-origin requests
- [ ] Document CORS settings

#### 11.4 Rate Limiting (Optional)
- [ ] Add rate limiting to public endpoints
- [ ] Prevent abuse of OpenAI API
- [ ] Consider SlowAPI or similar

#### 11.5 Input Validation
- [ ] Validate all API inputs with Pydantic
- [ ] Sanitize user inputs
- [ ] Prevent SQL injection (using parameterized queries)

---

### Phase 12: Testing

#### 12.1 Backend Tests
- [ ] Unit tests for services:
  - Data ingestion
  - Summarization
  - Embeddings
  - RAG
- [ ] Integration tests for API endpoints
- [ ] Test error scenarios
- [ ] Aim for >80% code coverage

#### 12.2 Frontend Tests
- [ ] Component tests (React Testing Library):
  - Table rendering
  - Filtering
  - Modal interactions
- [ ] Integration tests for user flows
- [ ] E2E tests (Playwright or Cypress) - optional

#### 12.3 Manual Testing
- [ ] Test complete user workflows
- [ ] Cross-browser testing
- [ ] Mobile testing
- [ ] Performance testing

---

### Phase 13: Documentation

#### 13.1 Code Documentation
- [ ] Add docstrings to all functions
- [ ] Type hints for Python code
- [ ] JSDoc comments for complex JS functions
- [ ] Inline comments for complex logic

#### 13.2 README Files
- [ ] Root README.md:
  - Project overview
  - Architecture diagram
  - Quick start guide
  - Technology stack
  - License
- [ ] Backend README.md:
  - Setup instructions
  - Environment variables
  - Running locally
  - API documentation link
  - Testing
- [ ] Frontend README.md:
  - Setup instructions
  - Development server
  - Build process
  - Deployment

#### 13.3 API Documentation
- [ ] FastAPI auto-generated docs (available at /docs)
- [ ] Add description to all endpoints
- [ ] Add examples to request/response models
- [ ] Document error codes

#### 13.4 User Guide
- [ ] Create simple user guide (optional):
  - How to search CRLs
  - Using filters
  - Understanding summaries
  - Asking questions
  - Exporting data

---

### Phase 14: Deployment Preparation

#### 14.1 Docker Setup (Optional but Recommended)
- [ ] Create `Dockerfile` for backend:
  - Multi-stage build
  - Copy only necessary files
  - Install dependencies
  - Expose port
- [ ] Create `Dockerfile` for frontend:
  - Build production bundle
  - Serve with nginx
- [ ] Create `docker-compose.yml`:
  - Backend service
  - Frontend service
  - Volume for DuckDB data
  - Environment variables

#### 14.2 Production Configuration
- [ ] Create production environment files
- [ ] Configure logging for production
- [ ] Set up error tracking (Sentry - optional)
- [ ] Optimize build settings

#### 14.3 Deployment Guide
- [ ] Document deployment steps
- [ ] Initial data load procedure
- [ ] Backup and restore procedures
- [ ] Monitoring and health checks

---

## Security Checklist

- [x] ✅ OpenAI API key stored in environment variable
- [x] ✅ API key never exposed to frontend
- [x] ✅ API key never logged
- [x] ✅ .env file in .gitignore
- [x] ✅ Pre-commit hook to prevent accidental secret exposure
- [x] ✅ CORS restricted to specific origins
- [x] ✅ All user inputs validated
- [ ] ✅ No sensitive data in error messages
- [ ] ✅ HTTPS in production (deployment consideration)
- [ ] ✅ Rate limiting on API endpoints (optional)
- [ ] ✅ No hardcoded secrets in code

---

## Key Design Decisions

### Why DuckDB?
- **Perfect for analytics**: Optimized for read-heavy workloads
- **Embedded**: No separate database server needed
- **JSON support**: Native JSON columns for raw data storage
- **Vector search**: Can handle embeddings with VSS extension or custom functions
- **Small footprint**: Perfect for 392 records, scales to millions
- **Serverless-friendly**: Single file database, easy backups

### Why Not PostgreSQL + pgvector?
- Overkill for this scale (392 records)
- Requires separate database server
- More complex setup and maintenance
- DuckDB provides everything we need

### RAG Strategy
- Embed summaries (shorter, more focused) rather than full text
- Use cosine similarity for retrieval
- Top-k=5 CRLs for context (adjustable)
- Fallback to keyword search if embeddings fail

### Summarization Approach
- Single paragraph (3-5 sentences)
- Focus on deficiencies, not boilerplate
- GPT-4o-mini for cost efficiency
- Cache summaries to avoid re-processing

### Data Update Strategy
- Daily bulk download (not real-time API calls)
- Detect new/changed CRLs by comparing IDs
- Only process new CRLs (incremental)
- Keep processing metadata to track status

---

## Cost Estimation

### OpenAI API Costs (Initial Load - 392 CRLs)

**Summarization (GPT-4o-mini):**
- Input: ~500 tokens/CRL × 392 = 196,000 tokens
- Output: ~100 tokens/CRL × 392 = 39,200 tokens
- Cost: $0.15 per 1M input tokens, $0.60 per 1M output tokens
- Total: ~$0.05

**Embeddings (text-embedding-3-small):**
- ~100 tokens/summary × 392 = 39,200 tokens
- Cost: $0.02 per 1M tokens
- Total: ~$0.001

**Total Initial Setup: < $0.10**

**Ongoing Costs:**
- Minimal (few new CRLs per day)
- Q&A costs depend on user activity

---

## Timeline Estimate

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1-2 | 1 day | Foundation, database setup |
| Phase 3 | 1 day | Data ingestion pipeline |
| Phase 4-5 | 2 days | AI services & RAG |
| Phase 6 | 0.5 day | Scheduled tasks |
| Phase 7 | 1.5 days | Backend API |
| Phase 8-9 | 2 days | Frontend core features |
| Phase 10 | 1 day | Frontend polish |
| Phase 11-12 | 1 day | Security & testing |
| Phase 13-14 | 1 day | Documentation & deployment |

**Total: ~11 days** (assuming focused full-time work)

---

## Success Metrics

- [ ] All 392 CRLs successfully ingested
- [ ] 100% summarization coverage
- [ ] 100% embedding coverage
- [ ] API response time < 500ms for list queries
- [ ] Q&A response time < 10s
- [ ] Frontend loads in < 2s
- [ ] Zero API key leaks
- [ ] Daily scheduled task runs reliably

---

## Future Enhancements (Post-MVP)

- [ ] Advanced analytics (trend analysis, deficiency categorization)
- [ ] Email alerts for new CRLs matching user criteria
- [ ] User accounts for saving searches/annotations
- [ ] Comparison tool (compare multiple CRLs)
- [ ] PDF viewer integration (if PDFs are accessible)
- [ ] Mobile app
- [ ] Export to other formats (JSON, Markdown)
- [ ] API rate limiting dashboard
- [ ] Multi-language support for summaries
- [ ] Integration with other FDA APIs (drug labels, adverse events)

---

*This plan provides a comprehensive roadmap for building a production-ready FDA CRL Explorer application with AI-powered features.*
