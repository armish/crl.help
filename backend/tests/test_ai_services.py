"""
Tests for AI services (summarization, embeddings, RAG).
"""

import pytest
from app.config import Settings
from app.services.summarization import SummarizationService
from app.services.embeddings import EmbeddingsService
from app.services.rag import RAGService


@pytest.fixture
def dry_run_settings():
    """Settings with dry-run mode enabled."""
    return Settings(
        openai_api_key="sk-dummy-key-for-testing-purposes",
        ai_dry_run=True,
        ai_dry_run_summary_chars=500,
        openai_summary_model="gpt-5-nano",
        openai_qa_model="gpt-5-nano",
        openai_embedding_model="text-embedding-3-large"  # 3072 dims
    )


@pytest.fixture
def summarization_service(dry_run_settings):
    """Summarization service in dry-run mode."""
    return SummarizationService(dry_run_settings)


@pytest.fixture
def embeddings_service(dry_run_settings):
    """Embeddings service in dry-run mode."""
    return EmbeddingsService(dry_run_settings)


@pytest.fixture
def rag_service(dry_run_settings):
    """RAG service in dry-run mode."""
    return RAGService(dry_run_settings)


class TestSummarizationService:
    """Test summarization service."""

    def test_summarize_crl_dry_run(self, summarization_service):
        """Test CRL summarization in dry-run mode."""
        crl_text = """
        This is a Complete Response Letter from the FDA.
        The application has been reviewed and several deficiencies were found.
        The clinical data was insufficient to demonstrate efficacy.
        Manufacturing processes need to be improved.
        """ * 10  # Make it longer

        summary = summarization_service.summarize_crl(crl_text)

        assert summary is not None
        assert isinstance(summary, str)
        assert "[DRY-RUN SUMMARY]" in summary
        assert len(summary) > 0

    def test_summarize_empty_text_raises_error(self, summarization_service):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            summarization_service.summarize_crl("")

    def test_summarize_very_long_text(self, summarization_service):
        """Test that very long texts are handled (no truncation in modern models)."""
        # Modern models (GPT-5, GPT-4o) support 128K-400K token contexts
        # CRLs are typically 5K-50K chars (1K-15K tokens), so no truncation needed
        long_text = "x" * 50000  # ~50K chars, ~15K tokens
        summary = summarization_service.summarize_crl(long_text)

        # Should work without truncation
        assert summary is not None
        assert isinstance(summary, str)
        assert "[DRY-RUN SUMMARY]" in summary

    def test_batch_summarize(self, summarization_service):
        """Test batch summarization."""
        crl_texts = [
            ("crl1", "This is the first CRL text with some content."),
            ("crl2", "This is the second CRL text with different content."),
            ("crl3", "This is the third CRL text."),
        ]

        results = summarization_service.batch_summarize(crl_texts)

        assert len(results) == 3
        for crl_id, summary, error in results:
            assert crl_id in ["crl1", "crl2", "crl3"]
            assert summary is not None  # All should succeed in dry-run
            assert error is None

    def test_batch_summarize_handles_errors(self, summarization_service):
        """Test that batch summarization handles individual errors."""
        crl_texts = [
            ("crl1", "Valid text"),
            ("crl2", ""),  # Empty text should fail
            ("crl3", "Another valid text"),
        ]

        results = summarization_service.batch_summarize(crl_texts)

        assert len(results) == 3
        # First should succeed
        assert results[0][1] is not None
        assert results[0][2] is None
        # Second should fail
        assert results[1][1] is None
        assert results[1][2] is not None
        # Third should succeed
        assert results[2][1] is not None
        assert results[2][2] is None


class TestEmbeddingsService:
    """Test embeddings service."""

    def test_generate_embedding_dry_run(self, embeddings_service):
        """Test embedding generation in dry-run mode."""
        text = "This is a test text for embedding generation."

        embedding = embeddings_service.generate_embedding(text)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == 3072  # text-embedding-3-large
        assert all(isinstance(x, float) for x in embedding)

    def test_generate_embedding_empty_text_raises_error(self, embeddings_service):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            embeddings_service.generate_embedding("")

    def test_generate_embedding_truncates_long_text(self, embeddings_service):
        """Test that very long texts are truncated."""
        long_text = "x" * 50000
        embedding = embeddings_service.generate_embedding(long_text, truncate=True)

        # Should still work despite truncation
        assert embedding is not None
        assert len(embedding) == 3072  # text-embedding-3-large

    def test_batch_generate_embeddings(self, embeddings_service):
        """Test batch embedding generation."""
        texts = [
            ("doc1", "This is the first document."),
            ("doc2", "This is the second document."),
            ("doc3", "This is the third document."),
        ]

        results = embeddings_service.batch_generate_embeddings(texts)

        assert len(results) == 3
        for doc_id, embedding, error in results:
            assert doc_id in ["doc1", "doc2", "doc3"]
            assert embedding is not None
            assert len(embedding) == 3072  # text-embedding-3-large
            assert error is None

    def test_batch_generate_embeddings_handles_errors(self, embeddings_service):
        """Test that batch embedding generation handles errors."""
        texts = [
            ("doc1", "Valid text"),
            ("doc2", ""),  # Empty text should fail
            ("doc3", "Another valid text"),
        ]

        results = embeddings_service.batch_generate_embeddings(texts)

        assert len(results) == 3
        # First should succeed
        assert results[0][1] is not None
        assert results[0][2] is None
        # Second should fail
        assert results[1][1] is None
        assert results[1][2] is not None
        # Third should succeed
        assert results[2][1] is not None
        assert results[2][2] is None

    def test_generate_query_embedding(self, embeddings_service):
        """Test query embedding generation."""
        query = "What are the main deficiencies in CRLs?"

        embedding = embeddings_service.generate_query_embedding(query)

        assert embedding is not None
        assert len(embedding) == 3072  # text-embedding-3-large

    def test_generate_query_embedding_empty_raises_error(self, embeddings_service):
        """Test that empty query raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            embeddings_service.generate_query_embedding("")

    def test_generate_combined_embedding(self, embeddings_service):
        """Test combined embedding generation."""
        texts = [
            "First text segment",
            "Second text segment",
            "Third text segment"
        ]

        combined = embeddings_service.generate_combined_embedding(texts)

        assert combined is not None
        assert len(combined) == 3072  # text-embedding-3-large

    def test_generate_combined_embedding_with_weights(self, embeddings_service):
        """Test combined embedding with custom weights."""
        texts = ["Text 1", "Text 2"]
        weights = [0.7, 0.3]

        combined = embeddings_service.generate_combined_embedding(texts, weights)

        assert combined is not None
        assert len(combined) == 3072  # text-embedding-3-large

    def test_generate_combined_embedding_invalid_weights(self, embeddings_service):
        """Test that invalid weights raise error."""
        texts = ["Text 1", "Text 2"]
        invalid_weights = [0.5, 0.3]  # Don't sum to 1.0

        with pytest.raises(ValueError, match="must sum to 1.0"):
            embeddings_service.generate_combined_embedding(texts, invalid_weights)


class TestRAGService:
    """Test RAG service."""

    def test_rag_service_initialization(self, rag_service):
        """Test RAG service initialization."""
        assert rag_service is not None
        assert rag_service.settings is not None
        assert rag_service.openai_client is not None
        assert rag_service.embeddings_service is not None

    def test_compute_confidence_single_crl(self, rag_service):
        """Test confidence computation with single CRL."""
        relevant_crls = [
            ("crl1", 0.9, {"text": "content"}),
        ]

        confidence = rag_service._compute_confidence(relevant_crls)

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # High similarity should give high confidence

    def test_compute_confidence_multiple_crls(self, rag_service):
        """Test confidence computation with multiple CRLs."""
        relevant_crls = [
            ("crl1", 0.9, {"text": "content"}),
            ("crl2", 0.8, {"text": "content"}),
            ("crl3", 0.7, {"text": "content"}),
        ]

        confidence = rag_service._compute_confidence(relevant_crls)

        assert 0.0 <= confidence <= 1.0

    def test_compute_confidence_empty_list(self, rag_service):
        """Test confidence computation with empty list."""
        confidence = rag_service._compute_confidence([])
        assert confidence == 0.0

    def test_create_qa_prompt(self, rag_service):
        """Test Q&A prompt creation."""
        question = "What are the main deficiencies?"
        context = "CRL 1: Manufacturing issues\nCRL 2: Clinical data insufficient"

        prompt = rag_service._create_qa_prompt(question, context)

        assert question in prompt
        assert context in prompt
        assert "CRL" in prompt

    def test_answer_question_empty_raises_error(self, rag_service):
        """Test that empty question raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            rag_service.answer_question("")

    def test_answer_question_no_relevant_crls(self, rag_service, monkeypatch):
        """Test answer_question when no relevant CRLs found."""
        # Mock _retrieve_similar_crls to return empty list
        monkeypatch.setattr(
            rag_service,
            "_retrieve_similar_crls",
            lambda query_embedding, top_k: []
        )

        result = rag_service.answer_question(
            "What are the common deficiencies?",
            save_to_db=False
        )

        assert result["question"] == "What are the common deficiencies?"
        assert "couldn't find" in result["answer"].lower()
        assert result["relevant_crls"] == []
        assert result["confidence"] == 0.0

    def test_answer_question_with_relevant_crls(self, rag_service, monkeypatch):
        """Test answer_question with relevant CRLs."""
        # Mock the retrieval to return fake CRLs
        mock_crls = [
            ("crl1", 0.85, {
                "application_number": ["NDA 123456"],
                "company_name": "Test Pharma",
                "letter_date": "2023-01-15",
                "text": "Manufacturing deficiencies were identified."
            }),
            ("crl2", 0.75, {
                "application_number": ["NDA 789012"],
                "company_name": "Another Pharma",
                "letter_date": "2023-02-20",
                "text": "Clinical data was insufficient."
            })
        ]

        monkeypatch.setattr(
            rag_service,
            "_retrieve_similar_crls",
            lambda query_embedding, top_k: mock_crls
        )

        result = rag_service.answer_question(
            "What are common deficiencies?",
            top_k=2,
            save_to_db=False
        )

        assert result["question"] == "What are common deficiencies?"
        assert result["answer"] is not None
        assert len(result["answer"]) > 0
        assert "[DRY-RUN SUMMARY]" in result["answer"]
        assert result["relevant_crls"] == ["crl1", "crl2"]
        assert 0.0 < result["confidence"] <= 1.0
        assert result["model"] == "gpt-5-nano"

    def test_retrieve_similar_crls_no_embeddings_raises_error(self, rag_service, monkeypatch):
        """Test _retrieve_similar_crls when no embeddings in database."""
        # Mock embedding repo to return empty list
        monkeypatch.setattr(
            rag_service.embedding_repo,
            "get_embeddings_for_search",
            lambda embedding_type: []
        )

        query_embedding = [0.1] * 3072  # text-embedding-3-large

        with pytest.raises(ValueError, match="No CRL embeddings found"):
            rag_service._retrieve_similar_crls(query_embedding, top_k=5)

    def test_retrieve_similar_crls_success(self, rag_service, monkeypatch):
        """Test _retrieve_similar_crls successfully retrieves CRLs."""
        # Mock embedding repo with optimized method
        mock_embeddings = [
            {"crl_id": "crl1", "embedding": [0.9] * 3072},
            {"crl_id": "crl2", "embedding": [0.5] * 3072},
            {"crl_id": "crl3", "embedding": [0.1] * 3072},
        ]

        monkeypatch.setattr(
            rag_service.embedding_repo,
            "get_embeddings_for_search",
            lambda embedding_type: mock_embeddings
        )

        # Mock CRL repo to return CRL data
        def mock_get_by_id(crl_id):
            return {
                "id": crl_id,
                "text": f"Text for {crl_id}",
                "company_name": "Test Company",
                "application_number": ["NDA 123"],
                "letter_date": "2023-01-01"
            }

        monkeypatch.setattr(
            rag_service.crl_repo,
            "get_by_id",
            mock_get_by_id
        )

        query_embedding = [0.8] * 3072  # text-embedding-3-large
        results = rag_service._retrieve_similar_crls(query_embedding, top_k=2)

        assert len(results) == 2
        assert all(len(result) == 3 for result in results)  # (id, score, data)
        assert results[0][0] in ["crl1", "crl2", "crl3"]
        assert isinstance(results[0][1], float)  # similarity score
        assert isinstance(results[0][2], dict)  # CRL data

    def test_generate_answer_truncates_long_text(self, rag_service):
        """Test that _generate_answer truncates very long CRL text."""
        long_text = "x" * 5000
        relevant_crls = [
            ("crl1", 0.9, {
                "application_number": ["NDA 123"],
                "company_name": "Test",
                "letter_date": "2023-01-01",
                "text": long_text
            })
        ]

        answer, crl_ids = rag_service._generate_answer(
            "What are the issues?",
            relevant_crls
        )

        assert answer is not None
        assert crl_ids == ["crl1"]
        assert "[DRY-RUN SUMMARY]" in answer

    def test_save_qa(self, rag_service, monkeypatch):
        """Test _save_qa saves Q&A to database."""
        saved_record = None

        def mock_create(record):
            nonlocal saved_record
            saved_record = record

        monkeypatch.setattr(
            rag_service.qa_repo,
            "create",
            mock_create
        )

        qa_data = {
            "question": "Test question?",
            "answer": "Test answer.",
            "relevant_crls": ["crl1", "crl2"],
            "model": "gpt-5-nano"
        }

        rag_service._save_qa(qa_data)

        assert saved_record is not None
        assert saved_record["question"] == "Test question?"
        assert saved_record["answer"] == "Test answer."
        assert saved_record["relevant_crl_ids"] == ["crl1", "crl2"]
        assert saved_record["model"] == "gpt-5-nano"
        assert "id" in saved_record

    def test_get_recent_questions(self, rag_service, monkeypatch):
        """Test get_recent_questions."""
        mock_questions = [
            {"id": "1", "question": "Q1?", "answer": "A1"},
            {"id": "2", "question": "Q2?", "answer": "A2"},
        ]

        monkeypatch.setattr(
            rag_service.qa_repo,
            "get_recent",
            lambda limit: mock_questions[:limit]
        )

        results = rag_service.get_recent_questions(limit=2)

        assert len(results) == 2
        assert results[0]["question"] == "Q1?"
        assert results[1]["question"] == "Q2?"


class TestRAGServiceWithRealEmbeddings:
    """Test RAG service with real embeddings from production database."""

    def test_retrieve_similar_crls_with_real_embeddings(self, rag_service, monkeypatch):
        """Test vector similarity search with real embeddings."""
        from tests.fixtures.sample_embeddings import get_sample_embeddings, get_sample_crl_data

        # Get real embeddings with 3072 dimensions
        real_samples = get_sample_embeddings(dimension=3072)
        assert len(real_samples) > 0, "Need at least one 3072-dim embedding sample"

        # Mock embedding repo to return real embeddings
        mock_embeddings = [
            {"crl_id": sample["crl_id"], "embedding": sample["embedding"]}
            for sample in real_samples
        ]

        monkeypatch.setattr(
            rag_service.embedding_repo,
            "get_embeddings_for_search",
            lambda embedding_type: mock_embeddings
        )

        # Mock CRL repo to return real CRL data
        def mock_get_by_id(crl_id):
            return get_sample_crl_data(crl_id)

        monkeypatch.setattr(
            rag_service.crl_repo,
            "get_by_id",
            mock_get_by_id
        )

        # Use the first real embedding as query (to ensure we get a match)
        query_embedding = real_samples[0]["embedding"]
        results = rag_service._retrieve_similar_crls(query_embedding, top_k=3)

        # Verify results
        assert len(results) > 0, "Should find similar CRLs"
        assert len(results) <= 3, "Should respect top_k limit"

        # First result should be the query itself (or very similar)
        top_crl_id, top_score, top_data = results[0]
        assert isinstance(top_score, float)
        assert 0.0 <= top_score <= 1.0, "Cosine similarity should be in [0, 1]"
        # Since we're querying with an embedding from the set, we should get high similarity
        assert top_score > 0.5, "Query against same embedding should have high similarity"

        # Verify CRL data structure
        assert top_data is not None
        assert "id" in top_data
        assert "company_name" in top_data
        assert "application_number" in top_data

    def test_vector_similarity_calculations_with_real_data(self):
        """Test that vector similarity calculations work correctly with real embeddings."""
        from tests.fixtures.sample_embeddings import get_sample_embeddings
        from app.utils.vector_utils import cosine_similarity

        real_samples = get_sample_embeddings(dimension=3072)
        if len(real_samples) < 2:
            pytest.skip("Need at least 2 real embeddings for similarity testing")

        emb1 = real_samples[0]["embedding"]
        emb2 = real_samples[1]["embedding"]

        # Test cosine similarity
        similarity = cosine_similarity(emb1, emb2)
        assert isinstance(similarity, float)
        assert -1.0 <= similarity <= 1.0, "Cosine similarity should be in [-1, 1]"

        # Self-similarity should be 1.0 (or very close due to floating point)
        self_similarity = cosine_similarity(emb1, emb1)
        assert abs(self_similarity - 1.0) < 0.0001, "Self-similarity should be ~1.0"

    def test_answer_question_with_real_embeddings(self, rag_service, monkeypatch):
        """Test full Q&A flow with real embeddings (offline mode)."""
        from tests.fixtures.sample_embeddings import get_sample_embeddings, get_sample_crl_data

        real_samples = get_sample_embeddings(dimension=3072)
        if len(real_samples) == 0:
            pytest.skip("Need real embeddings for this test")

        # Mock embedding repo
        mock_embeddings = [
            {"crl_id": sample["crl_id"], "embedding": sample["embedding"]}
            for sample in real_samples
        ]

        monkeypatch.setattr(
            rag_service.embedding_repo,
            "get_embeddings_for_search",
            lambda embedding_type: mock_embeddings
        )

        # Mock CRL repo
        def mock_get_by_id(crl_id):
            return get_sample_crl_data(crl_id)

        monkeypatch.setattr(
            rag_service.crl_repo,
            "get_by_id",
            mock_get_by_id
        )

        # Mock query embedding generation to use a real embedding
        # (simulates what would happen if we had a real query)
        query_embedding = real_samples[0]["embedding"]

        monkeypatch.setattr(
            rag_service.embeddings_service,
            "generate_query_embedding",
            lambda question: query_embedding
        )

        # Ask a question
        result = rag_service.answer_question(
            "What are the common deficiencies in Complete Response Letters?",
            top_k=3,
            save_to_db=False
        )

        # Verify result structure
        assert result is not None
        assert "question" in result
        assert "answer" in result
        assert "relevant_crls" in result
        assert "confidence" in result
        assert "model" in result

        # Should find relevant CRLs
        assert result["answer"] is not None
        assert "[DRY-RUN SUMMARY]" in result["answer"]
        assert isinstance(result["relevant_crls"], list)
        assert len(result["relevant_crls"]) > 0, "Should find at least one relevant CRL"
        assert 0.0 <= result["confidence"] <= 1.0

    def test_embedding_dimension_consistency(self):
        """Test that real embeddings have consistent dimensions."""
        from tests.fixtures.sample_embeddings import SAMPLE_EMBEDDINGS

        dimensions = [len(sample["embedding"]) for sample in SAMPLE_EMBEDDINGS]

        # All embeddings should be either 1536 or 3072
        for dim in dimensions:
            assert dim in [1536, 3072], f"Unexpected embedding dimension: {dim}"

        # Count by dimension
        dim_1536 = sum(1 for d in dimensions if d == 1536)
        dim_3072 = sum(1 for d in dimensions if d == 3072)

        print(f"\nEmbedding dimensions: {dim_1536} × 1536-dim, {dim_3072} × 3072-dim")

    def test_real_embeddings_are_normalized(self):
        """Test that real embeddings are properly normalized (or close to it)."""
        from tests.fixtures.sample_embeddings import get_sample_embeddings
        from app.utils.vector_utils import vector_magnitude
        import math

        for dim in [1536, 3072]:
            samples = get_sample_embeddings(dimension=dim)
            if not samples:
                continue

            for sample in samples:
                magnitude = vector_magnitude(sample["embedding"])
                # OpenAI embeddings are normalized, so magnitude should be close to 1.0
                # Allow some tolerance for floating point precision
                assert 0.9 < magnitude < 1.1, (
                    f"Embedding {sample['crl_id']} has unexpected magnitude: {magnitude}"
                )


class TestAIServicesIntegration:
    """Integration tests for AI services."""

    def test_summarization_embeddings_pipeline(
        self,
        dry_run_settings,
        summarization_service,
        embeddings_service
    ):
        """Test pipeline: text -> summary -> embedding."""
        crl_text = "This is a test CRL with important information about deficiencies."

        # Generate summary
        summary = summarization_service.summarize_crl(crl_text)
        assert summary is not None

        # Generate embedding of summary
        embedding = embeddings_service.generate_embedding(summary)
        assert embedding is not None
        assert len(embedding) == 3072  # text-embedding-3-large

    def test_dry_run_mode_saves_costs(self, dry_run_settings):
        """Test that dry-run mode doesn't make API calls."""
        # This is more of a documentation test
        # In dry-run mode, no actual API calls are made
        assert dry_run_settings.ai_dry_run is True

        # Create services
        summarization = SummarizationService(dry_run_settings)
        embeddings = EmbeddingsService(dry_run_settings)

        # These should work without API keys
        summary = summarization.summarize_crl("Test text")
        embedding = embeddings.generate_embedding("Test text")

        assert summary is not None
        assert embedding is not None
