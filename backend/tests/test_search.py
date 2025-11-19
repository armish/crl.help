"""
Unit tests for search functionality.

Tests both keyword search and semantic search capabilities,
including context snippet extraction, rate limiting, and reCAPTCHA.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.database import CRLRepository, SummaryRepository, EmbeddingRepository, init_db, get_db


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_client(test_env_vars):
    """Create a test client for the FastAPI app."""
    init_db()
    client = TestClient(app)
    return client


@pytest.fixture(scope="function")
def populated_db(test_env_vars):
    """
    Fixture that provides a database populated with test CRLs.

    Creates test CRLs with different content for search testing.
    """
    init_db()

    crl_repo = CRLRepository()
    summary_repo = SummaryRepository()

    # Create test CRLs
    test_crls = [
        {
            "id": "BLA123456_20240101",
            "application_number": ["BLA 123456"],
            "letter_date": "2024-01-01",
            "letter_year": "2024",
            "letter_type": "COMPLETE RESPONSE",
            "application_type": "BLA",
            "approval_status": "Unapproved",
            "company_name": "Pfizer Inc.",
            "company_address": "123 Main St",
            "company_rep": "John Doe",
            "approver_name": "Jane Smith",
            "approver_center": ["CDER"],
            "approver_title": "Director",
            "file_name": "test1.pdf",
            "text": "This is a letter from Pfizer regarding clinical deficiencies in their drug application. The study showed insufficient efficacy data.",
            "therapeutic_category": "Biologics",
            "product_name": "TestDrug-A",
            "indications": "Cancer treatment",
            "deficiency_reason": "Clinical"
        },
        {
            "id": "NDA789012_20240115",
            "application_number": ["NDA 789012"],
            "letter_date": "2024-01-15",
            "letter_year": "2024",
            "letter_type": "COMPLETE RESPONSE",
            "application_type": "NDA",
            "approval_status": "Unapproved",
            "company_name": "Moderna Therapeutics",
            "company_address": "456 Oak Ave",
            "company_rep": "Alice Johnson",
            "approver_name": "Bob Williams",
            "approver_center": ["CBER"],
            "approver_title": "Director",
            "file_name": "test2.pdf",
            "text": "Quality control issues were identified in the manufacturing process. Additional CMC data is required.",
            "therapeutic_category": "Small molecules",
            "product_name": "TestDrug-B",
            "indications": "Diabetes",
            "deficiency_reason": "CMC / Quality"
        },
        {
            "id": "BLA345678_20240201",
            "application_number": ["BLA 345678"],
            "letter_date": "2024-02-01",
            "letter_year": "2024",
            "letter_type": "COMPLETE RESPONSE",
            "application_type": "BLA",
            "approval_status": "Unapproved",
            "company_name": "Johnson & Johnson",
            "company_address": "789 Pine Rd",
            "company_rep": "Charlie Brown",
            "approver_name": "Diana Prince",
            "approver_center": ["CDER"],
            "approver_title": "Deputy Director",
            "file_name": "test3.pdf",
            "text": "The application lacks sufficient clinical data to support the proposed indication.",
            "therapeutic_category": "Biologics",
            "product_name": "TestDrug-C",
            "indications": "Rheumatoid arthritis",
            "deficiency_reason": "Clinical"
        },
    ]

    # Insert CRLs
    for crl in test_crls:
        crl_repo.create(crl)

    # Create summaries for some CRLs
    summaries = [
        {
            "id": "summary_1",
            "crl_id": "BLA123456_20240101",
            "summary": "FDA rejected Pfizer's BLA due to insufficient clinical efficacy data in the pivotal trial.",
            "model": "gpt-4",
            "tokens_used": 100
        },
        {
            "id": "summary_2",
            "crl_id": "NDA789012_20240115",
            "summary": "Moderna's NDA was rejected due to CMC and quality control deficiencies in manufacturing.",
            "model": "gpt-4",
            "tokens_used": 90
        },
    ]

    for summary in summaries:
        summary_repo.create(summary)

    yield

    # Cleanup is automatic with :memory: database


# ============================================================================
# CRLRepository.search_keywords() Tests
# ============================================================================

class TestCRLRepositorySearch:
    """Test cases for CRLRepository.search_keywords() method."""

    def test_search_keywords_company_name(self, populated_db):
        """Test searching by company name."""
        repo = CRLRepository()
        results, total = repo.search_keywords("Pfizer", limit=10, offset=0)

        assert total == 1
        assert len(results) == 1
        assert results[0]['company_name'] == "Pfizer Inc."
        assert 'company_name' in results[0]['matched_fields']
        assert 'company_name' in results[0]['match_snippets']

    def test_search_keywords_multiple_matches(self, populated_db):
        """Test searching term that appears in multiple CRLs."""
        repo = CRLRepository()
        results, total = repo.search_keywords("clinical", limit=10, offset=0)

        # Should match 2 CRLs (Pfizer and J&J both have "clinical" in text)
        assert total == 2
        assert len(results) == 2

    def test_search_keywords_in_summary(self, populated_db):
        """Test searching in AI-generated summaries."""
        repo = CRLRepository()
        results, total = repo.search_keywords("manufacturing", limit=10, offset=0)

        assert total >= 1
        # Check if summary field is included in matches
        moderna_result = [r for r in results if r['company_name'] == "Moderna Therapeutics"]
        assert len(moderna_result) == 1
        assert 'summary' in moderna_result[0]['matched_fields']

    def test_search_keywords_in_text(self, populated_db):
        """Test searching in full text content."""
        repo = CRLRepository()
        results, total = repo.search_keywords("efficacy", limit=10, offset=0)

        assert total >= 1
        pfizer_result = [r for r in results if r['company_name'] == "Pfizer Inc."]
        assert len(pfizer_result) == 1
        assert 'text' in pfizer_result[0]['matched_fields']

    def test_search_keywords_pagination(self, populated_db):
        """Test pagination in search results."""
        repo = CRLRepository()

        # Get first result
        results_page1, total = repo.search_keywords("clinical", limit=1, offset=0)
        assert len(results_page1) == 1
        assert total == 2

        # Get second result
        results_page2, total = repo.search_keywords("clinical", limit=1, offset=1)
        assert len(results_page2) == 1
        assert total == 2

        # Ensure different results
        assert results_page1[0]['id'] != results_page2[0]['id']

    def test_search_keywords_case_insensitive(self, populated_db):
        """Test that search is case insensitive."""
        repo = CRLRepository()

        results_lower, total_lower = repo.search_keywords("pfizer", limit=10, offset=0)
        results_upper, total_upper = repo.search_keywords("PFIZER", limit=10, offset=0)
        results_mixed, total_mixed = repo.search_keywords("PfIzEr", limit=10, offset=0)

        assert total_lower == total_upper == total_mixed == 1
        assert len(results_lower) == len(results_upper) == len(results_mixed) == 1

    def test_search_keywords_no_matches(self, populated_db):
        """Test search with no matches."""
        repo = CRLRepository()
        results, total = repo.search_keywords("nonexistent-term-xyz", limit=10, offset=0)

        assert total == 0
        assert len(results) == 0

    def test_search_keywords_empty_query(self, populated_db):
        """Test search with empty query."""
        repo = CRLRepository()
        results, total = repo.search_keywords("", limit=10, offset=0)

        assert total == 0
        assert len(results) == 0

    def test_search_keywords_whitespace_query(self, populated_db):
        """Test search with whitespace-only query."""
        repo = CRLRepository()
        results, total = repo.search_keywords("   ", limit=10, offset=0)

        assert total == 0
        assert len(results) == 0

    def test_extract_snippet_basic(self, populated_db):
        """Test context snippet extraction."""
        repo = CRLRepository()

        text = "This is some text before the keyword match here and some text after the match."
        snippet = repo._extract_snippet(text, "keyword", context_chars=20)

        assert snippet['match'] == "keyword"
        assert len(snippet['before']) > 0
        assert len(snippet['after']) > 0
        assert "text before" in snippet['before']
        assert "match here" in snippet['after']

    def test_extract_snippet_at_start(self, populated_db):
        """Test snippet extraction when match is at start of text."""
        repo = CRLRepository()

        text = "keyword is at the start of this text"
        snippet = repo._extract_snippet(text, "keyword", context_chars=20)

        assert snippet['match'] == "keyword"
        assert snippet['before'] == ""  # No text before
        assert len(snippet['after']) > 0

    def test_extract_snippet_at_end(self, populated_db):
        """Test snippet extraction when match is at end of text."""
        repo = CRLRepository()

        text = "This text ends with the keyword"
        snippet = repo._extract_snippet(text, "keyword", context_chars=20)

        assert snippet['match'] == "keyword"
        assert len(snippet['before']) > 0
        assert snippet['after'] == ""  # No text after

    def test_extract_snippet_case_preservation(self, populated_db):
        """Test that snippet preserves original case of match."""
        repo = CRLRepository()

        text = "This is some text with Pfizer in mixed case"
        snippet = repo._extract_snippet(text, "pfizer", context_chars=20)

        # Should preserve original case
        assert snippet['match'] == "Pfizer"

    def test_extract_snippet_with_ellipsis(self, populated_db):
        """Test that snippet adds ellipsis when truncated."""
        repo = CRLRepository()

        long_text = "A" * 200 + " keyword " + "B" * 200
        snippet = repo._extract_snippet(long_text, "keyword", context_chars=50)

        assert snippet['before'].startswith("...")
        assert snippet['after'].endswith("...")


# ============================================================================
# Keyword Search API Tests
# ============================================================================

class TestKeywordSearchAPI:
    """Test cases for /api/search/keyword endpoint."""

    def test_keyword_search_success(self, test_client, populated_db):
        """Test successful keyword search."""
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "Pfizer", "limit": 10, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "Pfizer"
        assert data["total"] >= 1
        assert len(data["results"]) >= 1

    def test_keyword_search_response_structure(self, test_client, populated_db):
        """Test that response has correct structure."""
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "clinical", "limit": 5, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

        # Check result structure
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "id" in result
            assert "company_name" in result
            assert "letter_date" in result
            assert "matched_fields" in result
            assert "match_snippets" in result

            # Check snippet structure
            if len(result["match_snippets"]) > 0:
                snippet_key = list(result["match_snippets"].keys())[0]
                snippet = result["match_snippets"][snippet_key]
                assert "before" in snippet
                assert "match" in snippet
                assert "after" in snippet

    def test_keyword_search_pagination(self, test_client, populated_db):
        """Test pagination in keyword search."""
        # First page
        response1 = test_client.post(
            "/api/search/keyword",
            json={"query": "clinical", "limit": 1, "offset": 0}
        )
        data1 = response1.json()

        # Second page
        response2 = test_client.post(
            "/api/search/keyword",
            json={"query": "clinical", "limit": 1, "offset": 1}
        )
        data2 = response2.json()

        assert data1["total"] == data2["total"]
        assert data1["has_more"] == True
        assert len(data1["results"]) == 1
        assert len(data2["results"]) == 1

        # Different results on different pages
        assert data1["results"][0]["id"] != data2["results"][0]["id"]

    def test_keyword_search_no_results(self, test_client, populated_db):
        """Test search with no results."""
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "nonexistent-xyz-term", "limit": 10, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert len(data["results"]) == 0
        assert data["has_more"] == False

    def test_keyword_search_invalid_limit(self, test_client, populated_db):
        """Test search with invalid limit."""
        # Limit too large
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "test", "limit": 200, "offset": 0}
        )
        assert response.status_code == 422  # Validation error

        # Limit too small
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "test", "limit": 0, "offset": 0}
        )
        assert response.status_code == 422  # Validation error

    def test_keyword_search_invalid_offset(self, test_client, populated_db):
        """Test search with negative offset."""
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "test", "limit": 10, "offset": -1}
        )
        assert response.status_code == 422  # Validation error

    def test_keyword_search_empty_query(self, test_client, populated_db):
        """Test search with empty query."""
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "", "limit": 10, "offset": 0}
        )
        # Should return validation error or empty results
        assert response.status_code in [200, 422]

    def test_keyword_search_missing_query(self, test_client, populated_db):
        """Test search without query parameter."""
        response = test_client.post(
            "/api/search/keyword",
            json={"limit": 10, "offset": 0}
        )
        assert response.status_code == 422  # Validation error

    def test_keyword_search_default_params(self, test_client, populated_db):
        """Test search with default parameters."""
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "clinical"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check defaults
        assert data["limit"] == 50  # Default limit
        assert data["offset"] == 0  # Default offset

    def test_keyword_search_multiple_fields(self, test_client, populated_db):
        """Test that search matches across multiple fields."""
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "Pfizer", "limit": 10, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()

        if len(data["results"]) > 0:
            result = data["results"][0]
            # Should match in company_name at minimum
            assert "company_name" in result["matched_fields"]
            # May also match in other fields
            assert len(result["matched_fields"]) >= 1

    def test_keyword_search_special_characters(self, test_client, populated_db):
        """Test search with special characters."""
        # Test with &
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "Johnson & Johnson", "limit": 10, "offset": 0}
        )
        assert response.status_code == 200

        # Test with parentheses
        response = test_client.post(
            "/api/search/keyword",
            json={"query": "NDA (789012)", "limit": 10, "offset": 0}
        )
        assert response.status_code == 200


# ============================================================================
# Semantic Search API Tests
# ============================================================================

class TestSemanticSearchAPI:
    """Test cases for /api/search/semantic endpoint."""

    async def test_semantic_search_success(
        self,
        test_client,
        populated_db
    ):
        """Test successful semantic search with valid reCAPTCHA."""
        # Mock all dependencies
        with patch('app.api.search.verify_recaptcha', new_callable=AsyncMock) as mock_verify, \
             patch('app.api.search.EmbeddingsService') as mock_embeddings_service, \
             patch('app.api.search.RAGService') as mock_rag_service:

            # Mock reCAPTCHA validation (success)
            mock_verify.return_value = (True, 0.9, "")

            # Mock embeddings service
            mock_embeddings_instance = MagicMock()
            mock_embeddings_instance.generate_query_embedding.return_value = [0.1] * 3072
            mock_embeddings_service.return_value = mock_embeddings_instance

            # Mock RAG service to return similar CRLs
            mock_rag_instance = MagicMock()
            mock_rag_instance._retrieve_similar_crls.return_value = [
                (
                    "BLA123456_20240101",
                    0.85,  # Cosine similarity (-1 to 1)
                    {
                        'id': 'BLA123456_20240101',
                        'company_name': 'Pfizer Inc.',
                        'letter_date': '2024-01-01',
                        'letter_year': '2024',
                        'application_number': ['BLA 123456'],
                        'application_type': 'BLA',
                        'therapeutic_category': 'Biologics',
                        'deficiency_reason': 'Clinical',
                        'summary': 'FDA rejected due to insufficient clinical efficacy data.',
                        'text': 'This is a letter regarding clinical deficiencies. The study showed insufficient efficacy data.'
                    }
                )
            ]
            mock_rag_service.return_value = mock_rag_instance

            # Make request
            response = test_client.post(
                "/api/search/semantic",
                json={
                    "query": "clinical efficacy studies",
                    "top_k": 5,
                    "captcha_token": "valid_token_123"
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert "results" in data
            assert "query" in data
            assert "total_results" in data
            assert data["query"] == "clinical efficacy studies"
            assert data["total_results"] == 1

            # Check result structure
            result = data["results"][0]
            assert result["id"] == "BLA123456_20240101"
            assert result["company_name"] == "Pfizer Inc."
            assert "similarity_score" in result
            assert "relevant_excerpts" in result

            # Check similarity score is normalized to 0-1 range
            # Cosine 0.85 -> (0.85 + 1) / 2 = 0.925
            assert result["similarity_score"] == 0.925

            # Check relevant excerpts are extracted
            assert isinstance(result["relevant_excerpts"], list)

    async def test_semantic_search_invalid_recaptcha(
        self,
        test_client,
        populated_db
    ):
        """Test semantic search with invalid reCAPTCHA token."""
        # Mock all dependencies
        with patch('app.api.search.is_recaptcha_enabled') as mock_is_enabled, \
             patch('app.api.search.verify_recaptcha', new_callable=AsyncMock) as mock_verify, \
             patch('app.api.search.EmbeddingsService') as mock_embeddings_service, \
             patch('app.api.search.RAGService') as mock_rag_service:

            # Enable reCAPTCHA for this test
            mock_is_enabled.return_value = True

            # Mock reCAPTCHA validation (failure)
            mock_verify.return_value = (False, 0.1, "reCAPTCHA score too low")

            # Mock other services (should not be reached but include for safety)
            mock_embeddings_instance = MagicMock()
            mock_embeddings_instance.generate_query_embedding.return_value = [0.1] * 3072
            mock_embeddings_service.return_value = mock_embeddings_instance

            mock_rag_instance = MagicMock()
            mock_rag_instance._retrieve_similar_crls.return_value = []
            mock_rag_service.return_value = mock_rag_instance

            response = test_client.post(
                "/api/search/semantic",
                json={
                    "query": "clinical efficacy",
                    "top_k": 5,
                    "captcha_token": "invalid_token"
                }
            )

            # Should be forbidden
            assert response.status_code == 403
            data = response.json()
            assert "reCAPTCHA validation failed" in data["detail"]

    async def test_semantic_search_recaptcha_disabled(
        self,
        test_client,
        populated_db
    ):
        """Test semantic search when reCAPTCHA is disabled (dev mode)."""
        # Mock all dependencies
        with patch('app.api.search.is_recaptcha_enabled') as mock_is_enabled, \
             patch('app.api.search.EmbeddingsService') as mock_embeddings_service, \
             patch('app.api.search.RAGService') as mock_rag_service:

            # Mock reCAPTCHA disabled
            mock_is_enabled.return_value = False

            # Mock embeddings and RAG services
            mock_embeddings_instance = MagicMock()
            mock_embeddings_instance.generate_query_embedding.return_value = [0.1] * 3072
            mock_embeddings_service.return_value = mock_embeddings_instance

            mock_rag_instance = MagicMock()
            mock_rag_instance._retrieve_similar_crls.return_value = []
            mock_rag_service.return_value = mock_rag_instance

            response = test_client.post(
                "/api/search/semantic",
                json={
                    "query": "clinical efficacy",
                    "top_k": 5,
                    "captcha_token": "any_token"
                }
            )

            # Should succeed without reCAPTCHA check
            assert response.status_code == 200

    def test_semantic_search_missing_captcha_token(self, test_client, populated_db):
        """Test semantic search without captcha_token."""
        response = test_client.post(
            "/api/search/semantic",
            json={
                "query": "clinical efficacy",
                "top_k": 5
            }
        )

        # Should fail validation
        assert response.status_code == 422

    def test_semantic_search_invalid_top_k(self, test_client, populated_db):
        """Test semantic search with invalid top_k values."""
        # top_k too large
        response = test_client.post(
            "/api/search/semantic",
            json={
                "query": "clinical efficacy",
                "top_k": 100,
                "captcha_token": "token"
            }
        )
        assert response.status_code == 422

        # top_k too small
        response = test_client.post(
            "/api/search/semantic",
            json={
                "query": "clinical efficacy",
                "top_k": 0,
                "captcha_token": "token"
            }
        )
        assert response.status_code == 422

    def test_semantic_search_query_too_short(self, test_client, populated_db):
        """Test semantic search with query too short."""
        response = test_client.post(
            "/api/search/semantic",
            json={
                "query": "abc",  # Less than 5 characters
                "top_k": 5,
                "captcha_token": "token"
            }
        )
        assert response.status_code == 422

    async def test_semantic_search_no_results(
        self,
        test_client,
        populated_db
    ):
        """Test semantic search with no similar results."""
        # Mock all dependencies
        with patch('app.api.search.verify_recaptcha', new_callable=AsyncMock) as mock_verify, \
             patch('app.api.search.EmbeddingsService') as mock_embeddings_service, \
             patch('app.api.search.RAGService') as mock_rag_service:

            # Mock reCAPTCHA validation (success)
            mock_verify.return_value = (True, 0.9, "")

            # Mock embeddings service
            mock_embeddings_instance = MagicMock()
            mock_embeddings_instance.generate_query_embedding.return_value = [0.1] * 3072
            mock_embeddings_service.return_value = mock_embeddings_instance

            # Mock RAG service to return no results
            mock_rag_instance = MagicMock()
            mock_rag_instance._retrieve_similar_crls.return_value = []
            mock_rag_service.return_value = mock_rag_instance

            response = test_client.post(
                "/api/search/semantic",
                json={
                    "query": "completely unrelated topic",
                    "top_k": 5,
                    "captcha_token": "valid_token"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_results"] == 0
            assert len(data["results"]) == 0


# ============================================================================
# reCAPTCHA Validation Tests
# ============================================================================

class TestRecaptchaValidation:
    """Test cases for reCAPTCHA validation utility."""

    @patch('app.utils.recaptcha.httpx.AsyncClient')
    async def test_verify_recaptcha_success(self, mock_client):
        """Test successful reCAPTCHA verification."""
        from app.utils.recaptcha import verify_recaptcha
        from app.config import Settings

        # Mock successful Google API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "score": 0.9,
            "action": "search",
            "challenge_ts": "2024-01-01T00:00:00Z"
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        settings = Settings(recaptcha_secret_key="test_secret_key")

        is_valid, score, error = await verify_recaptcha(
            token="valid_token",
            remote_ip="1.2.3.4",
            settings=settings
        )

        assert is_valid is True
        assert score == 0.9
        assert error == ""

    @patch('app.utils.recaptcha.httpx.AsyncClient')
    async def test_verify_recaptcha_low_score(self, mock_client):
        """Test reCAPTCHA verification with low score."""
        from app.utils.recaptcha import verify_recaptcha
        from app.config import Settings

        # Mock Google API response with low score
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "score": 0.2,
            "action": "search",
            "challenge_ts": "2024-01-01T00:00:00Z"
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        settings = Settings(
            recaptcha_secret_key="test_secret_key",
            recaptcha_min_score=0.5
        )

        is_valid, score, error = await verify_recaptcha(
            token="suspicious_token",
            remote_ip="1.2.3.4",
            settings=settings
        )

        assert is_valid is False
        assert score == 0.2
        assert "score too low" in error

    @patch('app.utils.recaptcha.httpx.AsyncClient')
    async def test_verify_recaptcha_failure(self, mock_client):
        """Test reCAPTCHA verification failure from Google."""
        from app.utils.recaptcha import verify_recaptcha
        from app.config import Settings

        # Mock failed Google API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error-codes": ["invalid-input-response", "timeout-or-duplicate"]
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        settings = Settings(recaptcha_secret_key="test_secret_key")

        is_valid, score, error = await verify_recaptcha(
            token="invalid_token",
            remote_ip="1.2.3.4",
            settings=settings
        )

        assert is_valid is False
        assert score == 0.0
        assert "verification failed" in error

    async def test_verify_recaptcha_missing_token(self):
        """Test reCAPTCHA verification with missing token."""
        from app.utils.recaptcha import verify_recaptcha
        from app.config import Settings

        settings = Settings(recaptcha_secret_key="test_secret_key")

        is_valid, score, error = await verify_recaptcha(
            token="",
            remote_ip="1.2.3.4",
            settings=settings
        )

        assert is_valid is False
        assert score == 0.0
        assert "Missing reCAPTCHA token" in error

    async def test_verify_recaptcha_disabled(self):
        """Test reCAPTCHA verification when disabled (no secret key)."""
        from app.utils.recaptcha import verify_recaptcha
        from app.config import Settings

        settings = Settings(recaptcha_secret_key="")

        is_valid, score, error = await verify_recaptcha(
            token="any_token",
            remote_ip="1.2.3.4",
            settings=settings
        )

        # Should skip validation and return success
        assert is_valid is True
        assert score == 1.0
        assert error == ""

    def test_is_recaptcha_enabled(self):
        """Test is_recaptcha_enabled helper function."""
        from app.utils.recaptcha import is_recaptcha_enabled
        from app.config import Settings

        # Enabled
        settings_enabled = Settings(recaptcha_secret_key="test_key")
        assert is_recaptcha_enabled(settings_enabled) is True

        # Disabled
        settings_disabled = Settings(recaptcha_secret_key="")
        assert is_recaptcha_enabled(settings_disabled) is False


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Test cases for search helper functions."""

    def test_extract_relevant_excerpts_basic(self):
        """Test basic excerpt extraction."""
        from app.api.search import _extract_relevant_excerpts

        text = """
        This is a sentence about clinical trials.
        Another sentence discusses manufacturing deficiencies.
        A third sentence mentions quality control issues.
        Finally, we have a sentence about regulatory compliance.
        """

        excerpts = _extract_relevant_excerpts(text, "clinical trials", max_excerpts=3)

        assert len(excerpts) >= 1
        assert any("clinical" in excerpt.lower() for excerpt in excerpts)

    def test_extract_relevant_excerpts_multiple_matches(self):
        """Test excerpt extraction with multiple keyword matches."""
        from app.api.search import _extract_relevant_excerpts

        text = """
        Clinical data shows efficacy in phase 2 trials.
        The clinical study design was robust.
        Additional clinical endpoints were measured.
        Manufacturing process validation was completed.
        """

        excerpts = _extract_relevant_excerpts(text, "clinical efficacy", max_excerpts=3)

        # Should find sentences with both "clinical" and "efficacy"
        assert len(excerpts) >= 1
        # First excerpt should have highest overlap
        if len(excerpts) > 0:
            assert "clinical" in excerpts[0].lower()

    def test_extract_relevant_excerpts_short_text(self):
        """Test excerpt extraction with very short text."""
        from app.api.search import _extract_relevant_excerpts

        text = "Short text here."
        excerpts = _extract_relevant_excerpts(text, "clinical", max_excerpts=3)

        # Should return empty for very short text
        assert len(excerpts) == 0

    def test_extract_relevant_excerpts_no_matches(self):
        """Test excerpt extraction with no keyword matches."""
        from app.api.search import _extract_relevant_excerpts

        text = """
        This is a long enough text with multiple sentences.
        It contains various information about different topics.
        But none of these sentences match the query keywords.
        """

        excerpts = _extract_relevant_excerpts(text, "unrelated keyword xyz", max_excerpts=3)

        # Should return empty list when no matches
        assert len(excerpts) == 0

    def test_extract_relevant_excerpts_truncation(self):
        """Test that long excerpts are truncated to 200 chars."""
        from app.api.search import _extract_relevant_excerpts

        # Create a very long sentence with the keyword
        long_sentence = "Clinical trial " + "word " * 100 + "conclusion."
        text = long_sentence

        excerpts = _extract_relevant_excerpts(text, "clinical", max_excerpts=1)

        if len(excerpts) > 0:
            # Should be truncated to 200 chars + "..."
            assert len(excerpts[0]) <= 203  # 200 + "..."
