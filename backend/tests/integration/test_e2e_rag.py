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
