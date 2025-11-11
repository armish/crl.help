# Sanity Checks for Backend Implementation

This document outlines the sanity check points to verify the backend is working correctly before proceeding to frontend implementation.

## Prerequisites

1. Set up environment variables:
```bash
export OPENAI_API_KEY="your-actual-openai-api-key"
export DATABASE_URL="postgresql://user:password@localhost:5432/crl_help"
```

2. Ensure PostgreSQL is running locally

## Sanity Check #1: Database Schema & Migrations

### Steps:
```bash
# 1. Create the database
createdb crl_help

# 2. Run migrations
cd backend
alembic upgrade head

# 3. Verify tables were created
psql crl_help -c "\dt"
```

### Expected Output:
You should see tables:
- `alembic_version`
- `clinical_trials`
- `trial_embeddings`
- `user_queries`
- `rag_results`

### Verification:
```bash
# Check the schema of clinical_trials table
psql crl_help -c "\d clinical_trials"

# Check the schema of trial_embeddings table
psql crl_help -c "\d trial_embeddings"
```

### Success Criteria:
- All tables created without errors
- Foreign key relationships are correct
- Indexes are created (check with `\d+ table_name`)

---

## Sanity Check #2: OpenAI API Integration Test

### Purpose:
Test real OpenAI API calls for embeddings and chat completions (not mocked).

### Test Script:
Create and run the following test script:

```bash
# Create test script
cat > backend/tests/integration/test_openai_real.py << 'EOF'
"""
Integration tests for real OpenAI API calls.
Run these manually with a real API key to verify integration.
"""
import os
import pytest
from app.services.embedding import EmbeddingService
from app.services.rag import RAGService
from app.core.config import settings

# Skip if no API key is set
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping real API tests"
)


def test_real_embedding_generation():
    """Test generating embeddings with real OpenAI API."""
    service = EmbeddingService()

    test_text = "This is a phase 3 clinical trial for breast cancer treatment."
    embedding = service.generate_embedding(test_text)

    # Verify embedding properties
    assert embedding is not None
    assert len(embedding) == 1536  # OpenAI ada-002 dimension
    assert all(isinstance(x, float) for x in embedding)
    print(f"✓ Generated embedding with {len(embedding)} dimensions")
    print(f"✓ First 5 values: {embedding[:5]}")


def test_real_chat_completion():
    """Test chat completion with real OpenAI API."""
    service = RAGService()

    context = """
    NCT12345678: A Phase 3 Study of Drug X in Breast Cancer Patients
    This study is evaluating the efficacy of Drug X in treating stage 2-3 breast cancer.
    """

    query = "What is this trial about?"

    response = service._generate_response(query, context)

    # Verify response properties
    assert response is not None
    assert len(response) > 0
    assert "breast cancer" in response.lower() or "drug x" in response.lower()
    print(f"✓ Generated response: {response[:200]}...")


def test_real_embeddings_batch():
    """Test batch embedding generation."""
    service = EmbeddingService()

    texts = [
        "Clinical trial for lung cancer",
        "Phase 2 study for diabetes treatment",
        "Randomized controlled trial for hypertension"
    ]

    embeddings = service.generate_embeddings_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 1536 for emb in embeddings)
    print(f"✓ Generated {len(embeddings)} embeddings in batch")


if __name__ == "__main__":
    print("\n=== Testing Real OpenAI API Integration ===\n")

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set. Please set it first.")
        exit(1)

    print("1. Testing embedding generation...")
    test_real_embedding_generation()

    print("\n2. Testing chat completion...")
    test_real_chat_completion()

    print("\n3. Testing batch embeddings...")
    test_real_embeddings_batch()

    print("\n✅ All OpenAI API integration tests passed!\n")
EOF

# Run the test script
cd backend
python -m pytest tests/integration/test_openai_real.py -v -s
# Or run directly:
# python tests/integration/test_openai_real.py
```

### Success Criteria:
- Embeddings are generated successfully (1536 dimensions)
- Chat completions return relevant responses
- No API errors or rate limiting issues
- Batch processing works correctly

---

## Sanity Check #3: End-to-End RAG Flow

### Purpose:
Test the complete RAG pipeline: document indexing, embedding storage, retrieval, and response generation.

### Test Script:

```bash
# Create E2E test script
cat > backend/tests/integration/test_e2e_rag.py << 'EOF'
"""
End-to-end test for the complete RAG flow.
Tests: Index document -> Store embeddings -> Query -> Retrieve -> Generate response
"""
import os
import pytest
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.clinical_trial import ClinicalTrial
from app.models.embedding import TrialEmbedding
from app.services.embedding import EmbeddingService
from app.services.vectordb import VectorDBService
from app.services.rag import RAGService
from datetime import date

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping E2E tests"
)


def setup_database():
    """Ensure database is set up."""
    Base.metadata.create_all(bind=engine)


def test_e2e_rag_flow():
    """Complete end-to-end test of RAG system."""
    print("\n=== Starting End-to-End RAG Flow Test ===\n")

    # Setup
    setup_database()
    db: Session = SessionLocal()

    try:
        # Step 1: Create a sample clinical trial
        print("1. Creating sample clinical trial...")
        trial = ClinicalTrial(
            nct_id="NCT99999999",
            title="Phase 3 Study of Novel Immunotherapy in Advanced Melanoma",
            brief_summary="""
            This is a randomized, double-blind, placebo-controlled study to evaluate
            the efficacy and safety of a novel immunotherapy agent in patients with
            advanced melanoma who have failed prior therapy. The primary endpoint is
            overall survival.
            """,
            detailed_description="""
            This phase 3 clinical trial will enroll 500 patients with advanced melanoma
            (stage III or IV) who have progressed on at least one prior systemic therapy.
            Patients will be randomized 2:1 to receive either the novel immunotherapy
            agent at 240mg IV every 2 weeks or placebo. Treatment will continue until
            disease progression, unacceptable toxicity, or completion of 2 years.

            Key inclusion criteria:
            - Histologically confirmed melanoma
            - Stage III unresectable or Stage IV disease
            - ECOG performance status 0-1
            - Adequate organ function

            Primary endpoint: Overall survival
            Secondary endpoints: Progression-free survival, objective response rate,
            duration of response, and safety.
            """,
            phase="Phase 3",
            study_type="Interventional",
            overall_status="Recruiting",
            start_date=date(2024, 1, 1),
            completion_date=date(2026, 12, 31),
            enrollment=500,
            conditions=["Melanoma", "Advanced Melanoma", "Stage III Melanoma"],
            interventions=["Novel Immunotherapy Agent", "Placebo"],
            sponsor="Example Pharma Inc",
            metadata_={"test": True}
        )
        db.add(trial)
        db.commit()
        db.refresh(trial)
        print(f"   ✓ Created trial: {trial.nct_id}")

        # Step 2: Generate embeddings
        print("\n2. Generating embeddings for trial content...")
        embedding_service = EmbeddingService()

        # Combine trial information for embedding
        trial_text = f"""
        {trial.title}

        Brief Summary: {trial.brief_summary}

        Detailed Description: {trial.detailed_description}

        Phase: {trial.phase}
        Conditions: {', '.join(trial.conditions)}
        Interventions: {', '.join(trial.interventions)}
        """

        embedding_vector = embedding_service.generate_embedding(trial_text)
        print(f"   ✓ Generated embedding vector ({len(embedding_vector)} dimensions)")

        # Step 3: Store in vector database
        print("\n3. Storing embeddings in vector database...")
        vectordb_service = VectorDBService()

        vectordb_service.add_embeddings(
            embeddings=[embedding_vector],
            documents=[trial_text],
            metadatas=[{
                "nct_id": trial.nct_id,
                "trial_id": trial.id,
                "type": "full_text"
            }],
            ids=[f"{trial.nct_id}_full"]
        )
        print(f"   ✓ Stored embedding in ChromaDB")

        # Also store in database
        trial_embedding = TrialEmbedding(
            trial_id=trial.id,
            embedding_vector=embedding_vector,
            text_content=trial_text,
            embedding_type="full_text"
        )
        db.add(trial_embedding)
        db.commit()
        print(f"   ✓ Stored embedding in PostgreSQL")

        # Step 4: Query the system
        print("\n4. Testing retrieval with queries...")

        test_queries = [
            "What trials are available for advanced melanoma?",
            "Are there any immunotherapy trials for stage 4 melanoma?",
            "What is the primary endpoint of melanoma trials?"
        ]

        for query in test_queries:
            print(f"\n   Query: '{query}'")

            # Generate query embedding
            query_embedding = embedding_service.generate_embedding(query)

            # Retrieve relevant trials
            results = vectordb_service.query(
                query_embeddings=[query_embedding],
                n_results=3
            )

            print(f"   ✓ Retrieved {len(results['documents'][0])} relevant documents")

            # Check if our trial was retrieved
            if results['documents'][0]:
                top_doc = results['documents'][0][0]
                if "melanoma" in top_doc.lower() and "immunotherapy" in top_doc.lower():
                    print(f"   ✓ Correct trial retrieved!")
                    print(f"   ✓ Similarity score: {1 - results['distances'][0][0]:.4f}")

        # Step 5: Generate RAG response
        print("\n5. Testing full RAG response generation...")
        rag_service = RAGService(db)

        query = "What immunotherapy trials are available for melanoma patients?"
        response = rag_service.query(query, top_k=3)

        print(f"\n   Query: '{query}'")
        print(f"   Response: {response.answer[:300]}...")
        print(f"   ✓ Retrieved {len(response.retrieved_trials)} relevant trials")
        print(f"   ✓ Generated response in {response.response_time_ms:.2f}ms")

        # Verify response quality
        assert response.answer is not None
        assert len(response.answer) > 0
        assert len(response.retrieved_trials) > 0
        assert response.retrieved_trials[0]["nct_id"] == trial.nct_id

        print("\n✅ End-to-End RAG Flow Test PASSED!\n")

    finally:
        # Cleanup
        db.query(TrialEmbedding).filter(TrialEmbedding.trial_id == trial.id).delete()
        db.query(ClinicalTrial).filter(ClinicalTrial.nct_id == "NCT99999999").delete()
        db.commit()
        db.close()

        # Clean up vector database
        try:
            vectordb_service.delete_collection()
        except:
            pass


if __name__ == "__main__":
    test_e2e_rag_flow()
EOF

# Run the E2E test
cd backend
python tests/integration/test_e2e_rag.py
```

### Success Criteria:
- Clinical trial is created in database ✓
- Embeddings are generated successfully ✓
- Embeddings are stored in both ChromaDB and PostgreSQL ✓
- Queries retrieve the correct document ✓
- RAG response is relevant and accurate ✓
- All components work together seamlessly ✓

---

## Running All Sanity Checks

To run all sanity checks in sequence:

```bash
#!/bin/bash
# sanity_check_all.sh

echo "==================================="
echo "Running All Backend Sanity Checks"
echo "==================================="

# Check prerequisites
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is not set"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL is not set"
    exit 1
fi

echo ""
echo "✓ Prerequisites checked"
echo ""

# Sanity Check #1: Database
echo "--- Sanity Check #1: Database Schema ---"
cd backend
alembic upgrade head
if [ $? -eq 0 ]; then
    echo "✅ Database migrations successful"
else
    echo "❌ Database migrations failed"
    exit 1
fi

# Sanity Check #2: OpenAI API
echo ""
echo "--- Sanity Check #2: OpenAI API Integration ---"
python tests/integration/test_openai_real.py
if [ $? -eq 0 ]; then
    echo "✅ OpenAI API integration successful"
else
    echo "❌ OpenAI API integration failed"
    exit 1
fi

# Sanity Check #3: E2E RAG
echo ""
echo "--- Sanity Check #3: End-to-End RAG Flow ---"
python tests/integration/test_e2e_rag.py
if [ $? -eq 0 ]; then
    echo "✅ End-to-End RAG flow successful"
else
    echo "❌ End-to-End RAG flow failed"
    exit 1
fi

echo ""
echo "==================================="
echo "✅ All Sanity Checks PASSED!"
echo "==================================="
echo ""
echo "Backend is ready for frontend integration!"
```

---

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
pg_isready

# Check database exists
psql -l | grep crl_help

# Reset database if needed
dropdb crl_help && createdb crl_help
cd backend && alembic upgrade head
```

### OpenAI API Issues
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key with curl
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### ChromaDB Issues
```bash
# ChromaDB data is stored in backend/chroma_data/
# To reset:
rm -rf backend/chroma_data/
```

---

## Next Steps

After all sanity checks pass:
1. Document any issues or edge cases discovered
2. Proceed to frontend implementation
3. Set up integration tests between frontend and backend
4. Prepare for deployment

