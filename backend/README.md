# FDA CRL Explorer - Backend

Backend API for the FDA Complete Response Letters Explorer application.

## Technology Stack

- **Framework**: FastAPI (async, modern, auto-generated API docs)
- **Database**: DuckDB (embedded, excellent JSON support, analytics-optimized)
- **AI Services**: OpenAI API (GPT-4o-mini for summarization, text-embedding-3-small for embeddings)
- **Task Scheduling**: APScheduler (lightweight, in-process scheduler)
- **Data Processing**: pandas, httpx

## Setup

### Prerequisites

- Python 3.9+
- OpenAI API key

### Installation

1. **Create and activate virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

4. **Required environment variable:**
   - `OPENAI_API_KEY`: Your OpenAI API key (get from https://platform.openai.com/api-keys)

### Running the Application

**Development server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access the API:**
- API: http://localhost:8000/api
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Environment Variables

All configuration is managed through environment variables. See `.env.example` for a complete list.

**Required:**
- `OPENAI_API_KEY` - OpenAI API key for AI services

**Optional (with defaults):**
- `DATABASE_PATH` - Path to DuckDB database (default: `./data/crl_explorer.duckdb`)
- `FDA_BULK_APPROVED_URL` - URL for approved CRLs bulk download
- `FDA_BULK_UNAPPROVED_URL` - URL for unapproved CRLs bulk download
- `SCHEDULE_HOUR` - Hour (0-23) for daily data pipeline (default: 2)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `CORS_ORIGINS` - Comma-separated allowed CORS origins (default: http://localhost:5173)

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management (Pydantic Settings)
│   ├── database.py          # DuckDB connection & repositories
│   ├── models.py            # Pydantic models (request/response)
│   ├── schemas.py           # Database schemas (SQL)
│   │
│   ├── api/                 # API route handlers
│   │   ├── __init__.py
│   │   ├── crls.py          # CRL CRUD endpoints
│   │   ├── stats.py         # Statistics endpoints
│   │   ├── qa.py            # Q&A endpoints
│   │   └── export.py        # Export endpoints
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── data_ingestion.py    # Download & parse FDA data
│   │   ├── data_processor.py    # Process & store CRLs
│   │   ├── summarization.py     # OpenAI summarization
│   │   ├── embeddings.py        # OpenAI embeddings generation
│   │   ├── rag.py               # RAG: retrieval + generation
│   │   └── export_service.py    # Export to CSV/Excel
│   │
│   ├── tasks/               # Scheduled tasks
│   │   ├── __init__.py
│   │   └── scheduler.py     # APScheduler setup & jobs
│   │
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── openai_client.py     # OpenAI API wrapper
│       ├── vector_utils.py      # Vector similarity functions
│       └── logging_config.py    # Logging setup
│
├── data/                    # Local data directory
│   ├── raw/                 # Downloaded bulk data
│   ├── processed/           # Processed data
│   └── crl_explorer.duckdb  # DuckDB database file
│
├── tests/                   # Backend tests
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_services.py
│   └── test_rag.py
│
├── requirements.txt         # Python dependencies
├── .env.example            # Example environment variables
└── README.md               # This file
```

## Development

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Add docstrings to all modules, classes, and functions
- Keep functions focused and small

### Testing

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## API Endpoints

Once the application is running, comprehensive API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Security

- **Never commit `.env` file** - it contains sensitive API keys
- **API keys are backend-only** - never exposed to frontend
- **CORS is restricted** - only configured origins allowed
- **Input validation** - all inputs validated with Pydantic

## License

See root LICENSE file.
