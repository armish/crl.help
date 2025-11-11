# Integration Tests - TODO

## Status

The integration test files created earlier were incompatible with the actual codebase structure.
They were removed to fix CI failures.

## What Needs to Be Done

Create integration tests specific to the **FDA CRL Explorer** application that:

1. **Match the actual architecture:**
   - DuckDB database (not PostgreSQL/SQLAlchemy)
   - CRL (Complete Response Letters) data model
   - `EmbeddingsService` (note the 's')
   - Existing schema from `app/schemas.py`

2. **Test real OpenAI API integration:**
   - Embedding generation for CRL text
   - RAG query answering
   - Summarization

3. **Test end-to-end workflows:**
   - Ingest CRL data
   - Generate embeddings
   - Query with RAG
   - Generate summaries

## Current Application Structure

### Database
- **Type:** DuckDB (embedded SQL database)
- **Tables:**
  - `crls` - Raw CRL data from FDA API
  - `crl_summaries` - AI-generated summaries
  - `crl_embeddings` - Vector embeddings for RAG
  - `qa_annotations` - User questions and AI answers
  - `processing_metadata` - Processing status tracking

### Services
- `app/services/embeddings.py` - `EmbeddingsService` class
- `app/services/rag.py` - RAG query service
- `app/services/summarization.py` - CRL summarization
- `app/services/data_ingestion.py` - FDA data ingestion
- `app/services/data_processor.py` - Data processing

### Testing Strategy

Integration tests should:
1. Use the `@pytest.mark.requires_openai` marker
2. Be skipped in CI (check for `OPENAI_API_KEY`)
3. Test against real OpenAI API when run locally
4. Use DuckDB in-memory or temporary database
5. Clean up after themselves

## Example Structure (Not Implemented)

```python
import pytest
from app.config import get_settings
from app.database import DatabaseConnection
from app.services.embeddings import EmbeddingsService

@pytest.mark.requires_openai
def test_embeddings_generation():
    \"\"\"Test generating embeddings for CRL text.\"\"\"
    settings = get_settings()
    service = EmbeddingsService(settings)

    sample_text = "Complete Response Letter for NDA 123456..."
    embedding = service.generate_embedding(sample_text)

    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)

# More tests needed...
```

## Running Integration Tests (When Implemented)

```bash
# Run only integration tests
pytest -m requires_openai

# Skip integration tests
pytest -m "not requires_openai"
```

## See Also

- Existing unit tests in `backend/tests/`
- `backend/pytest.ini` - Test configuration with markers
- `backend/app/` - Application source code
