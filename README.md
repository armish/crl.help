# crl.help

[![Backend Tests](https://github.com/armish/crl.help/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/armish/crl.help/actions/workflows/backend-tests.yml)
[![Frontend Tests](https://github.com/armish/crl.help/actions/workflows/frontend-tests.yml/badge.svg)](https://github.com/armish/crl.help/actions/workflows/frontend-tests.yml)
[![Docker Build](https://github.com/armish/crl.help/actions/workflows/docker-build.yml/badge.svg)](https://github.com/armish/crl.help/actions/workflows/docker-build.yml)

FDA Complete Response Letter (CRL) Explorer - A web application for exploring and analyzing FDA Complete Response Letters with AI-powered insights.

Current address: [https://crl.help](https://crl.help))

## Quick Start

### Option 1: Docker (Recommended)

The easiest way to run the application is using Docker:

```bash
# Pull the latest image
docker pull ghcr.io/armish/crl.help:latest

# Run the container
docker run -d \
  -p 80:80 \
  -v ./data:/app/backend/data \
  ghcr.io/armish/crl.help:latest
```

The application will be available at `http://localhost`

For detailed Docker instructions including Docker Compose, environment variables, and deployment options, see [Docker.md](docker/Docker.md).

### Option 2: Local Development

#### Prerequisites

- Python 3.9+ (for backend)
- Node.js 18+ (for frontend)
- DuckDB (installed automatically)

#### Running the Application

#### 1. Start the Backend

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run the backend server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

#### 2. Start the Frontend

In a new terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

The frontend will be available at `http://localhost:5173/` (or the next available port)

#### 3. View the Application

Open your browser and navigate to `http://localhost:5173/`

You should see:
- **Statistics Dashboard** with interactive charts showing CRL data
- **Filter Panel** with search, status, year, and company filters
- **CRL Table** (coming soon in Phase 9.3)

### Running Tests

#### Backend Tests

```bash
cd backend
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ -v --cov=app --cov-report=html
```

#### Frontend Tests

```bash
cd frontend
npm test
```

Run with coverage:
```bash
npm run test:coverage
```

### Development Features

#### Backend
- FastAPI with automatic OpenAPI documentation
- DuckDB for high-performance analytics
- Comprehensive test coverage with pytest
- Automatic code reloading in development

#### Frontend
- React 19 with Vite for fast development
- TailwindCSS for styling
- React Query for data fetching
- Zustand for state management
- Recharts for interactive data visualization
- Vitest + React Testing Library for testing

### Project Structure

```
crl.help/
├── backend/          # FastAPI backend
│   ├── app/         # Application code
│   ├── tests/       # Backend tests
│   └── data/        # Data directory
├── frontend/        # React frontend
│   ├── src/         # Source code
│   └── tests/       # Frontend tests
└── README.md        # This file
```

### Data Ingestion

The application requires FDA CRL data to be loaded and processed. This is a one-time setup process that takes approximately **30 minutes**.

#### Quick Start (Automated)

The easiest way to ingest data is using the automated script:

```bash
cd backend

# Set your OpenAI API key (required for AI features)
export OPENAI_API_KEY=your_api_key_here

# Run the automated ingestion pipeline
python ingest_data.py
```

The script will:
1. Download FDA CRL data from the openFDA API
2. Generate AI-powered summaries for each CRL
3. Extract product indications using AI
4. Extract product names using AI
5. Classify deficiency reasons
6. Classify therapeutic categories
7. Set the last data update timestamp

The script includes:
- Interactive confirmation prompts
- Progress tracking with time estimates
- Automatic cleanup of old data (with confirmation)
- Error handling and recovery
- Colored terminal output for better readability

#### Manual Process (Advanced)

If you prefer to run steps individually:

```bash
cd backend

# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here

# Clean old data (optional)
rm -f data/crl_explorer.duckdb
rm -f data/raw/*

# Run each step
python load_data.py                      # ~2 minutes
python generate_summaries.py             # ~15 minutes
python extract_indications.py            # ~5 minutes
python extract_product_name.py           # ~3 minutes
python classify_crl_reasons.py           # ~3 minutes
python classify_crl_tx_category.py       # ~3 minutes
python set_last_update.py                # <1 minute
```

### Environment Variables

The application can be configured with these environment variables:

**Backend:**
- `DATABASE_PATH`: Path to DuckDB database (default: `data/crl.duckdb`)
- `OPENAI_API_KEY`: OpenAI API key for AI features (required for data ingestion)

**Frontend:**
- `VITE_API_BASE_URL`: Backend API URL (default: `http://localhost:8000`)

### Next Steps

See individual documentation files for more details:
- [Docker Documentation](docker/Docker.md) - Docker deployment and configuration
- [Backend README](backend/README.md) - API documentation and development
- [Frontend README](frontend/README.md) - UI components and testing
