# Quick Start: Running Sanity Checks

## Prerequisites Setup (5 minutes)

```bash
# 1. Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# 2. Set your database URL (or use default)
export DATABASE_URL="postgresql://localhost:5432/crl_help"

# 3. Ensure PostgreSQL is running
# On macOS: brew services start postgresql
# On Linux: sudo systemctl start postgresql
```

## Option 1: Run All Checks at Once (Recommended)

```bash
# Single command to run all sanity checks
./run_sanity_checks.sh
```

This will:
- ✓ Check prerequisites
- ✓ Create database if needed
- ✓ Run migrations
- ✓ Test OpenAI API integration
- ✓ Test end-to-end RAG flow

**Expected time:** 2-3 minutes

---

## Option 2: Run Individual Checks

### Sanity Check #1: Database Only

```bash
cd backend
alembic upgrade head
psql crl_help -c "\dt"  # List all tables
```

**What to verify:**
- Tables created: `clinical_trials`, `trial_embeddings`, `user_queries`, `rag_results`
- No migration errors

### Sanity Check #2: OpenAI API Only

```bash
cd backend
python tests/integration/test_openai_real.py
```

**What to verify:**
- Embeddings generated (1536 dimensions)
- Chat completions return relevant responses
- Batch processing works

### Sanity Check #3: End-to-End RAG Only

```bash
cd backend
python tests/integration/test_e2e_rag.py
```

**What to verify:**
- Trial created in database
- Embeddings stored in ChromaDB and PostgreSQL
- Queries retrieve correct documents
- RAG generates relevant responses

---

## Inspecting the Database

```bash
# Connect to database
psql crl_help

# View all trials
SELECT nct_id, title, phase, overall_status FROM clinical_trials;

# View all embeddings
SELECT trial_id, embedding_type, LENGTH(text_content) as content_length
FROM trial_embeddings;

# View queries
SELECT query_text, response_time_ms
FROM user_queries
ORDER BY created_at DESC
LIMIT 5;

# Exit psql
\q
```

---

## Testing Specific Scenarios

### Test 1: Add a Custom Trial

```python
# In backend directory, run Python shell
python

from app.db.session import SessionLocal
from app.models.clinical_trial import ClinicalTrial
from datetime import date

db = SessionLocal()

trial = ClinicalTrial(
    nct_id="NCT00000001",
    title="My Test Trial",
    brief_summary="This is a test",
    phase="Phase 2",
    study_type="Interventional",
    overall_status="Recruiting",
    start_date=date.today(),
    conditions=["Cancer"],
    interventions=["Drug X"]
)

db.add(trial)
db.commit()
print(f"Created trial: {trial.id}")

# Verify
db.query(ClinicalTrial).filter_by(nct_id="NCT00000001").first()

db.close()
```

### Test 2: Query the RAG System

```python
from app.services.rag import RAGService
from app.db.session import SessionLocal

db = SessionLocal()
rag = RAGService(db)

# Test query
response = rag.query("What trials are available for cancer?", top_k=5)

print(f"Answer: {response.answer}")
print(f"Found {len(response.retrieved_trials)} trials")
print(f"Response time: {response.response_time_ms}ms")

for trial in response.retrieved_trials:
    print(f"  - {trial['nct_id']}: {trial['title']}")

db.close()
```

---

## Troubleshooting

### Error: "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="sk-your-key-here"
echo $OPENAI_API_KEY  # Verify it's set
```

### Error: "database does not exist"
```bash
createdb crl_help
cd backend && alembic upgrade head
```

### Error: "Connection refused" (PostgreSQL)
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

### Error: OpenAI API rate limits
- Wait a few seconds and retry
- Check your API usage at platform.openai.com
- Upgrade your API plan if needed

---

## What's Next?

After all sanity checks pass:

1. **Review the test outputs** - Look for any warnings or unexpected behavior
2. **Inspect the database** - Verify data looks correct
3. **Test edge cases** - Try unusual queries, empty inputs, etc.
4. **Proceed to frontend** - Once backend is solid, start on the UI

---

## Performance Benchmarks

Expected performance (will vary based on API latency):

| Operation | Expected Time |
|-----------|--------------|
| Generate embedding | 100-500ms |
| Chat completion | 500-2000ms |
| Vector search | 10-50ms |
| Full RAG query | 1-3 seconds |

---

## Files Created

- `SANITY_CHECKS.md` - Detailed sanity check documentation
- `run_sanity_checks.sh` - Automated test runner script
- `backend/tests/integration/test_openai_real.py` - OpenAI API tests
- `backend/tests/integration/test_e2e_rag.py` - End-to-end RAG tests

---

## Need Help?

- Check `SANITY_CHECKS.md` for detailed troubleshooting
- Review test output for specific error messages
- Verify all prerequisites are properly set up
