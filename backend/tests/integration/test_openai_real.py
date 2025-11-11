"""
Integration tests for real OpenAI API calls.
Run these manually with a real API key to verify integration.
"""
import os
import pytest
from app.services.embedding import EmbeddingService
from app.services.rag import RAGService

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
