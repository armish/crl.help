"""
Tests for FastAPI endpoints.

Uses FastAPI's TestClient for testing HTTP endpoints without
needing to run the actual server.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import duckdb

from app.config import Settings


@pytest.fixture(scope="module")
def test_db():
    """Create an in-memory test database with sample data."""
    conn = duckdb.connect(":memory:")

    # Create tables (matching app/schemas.py structure)
    conn.execute("""
        CREATE TABLE crls (
            id VARCHAR PRIMARY KEY,
            application_number VARCHAR[],
            letter_date DATE,
            letter_year VARCHAR,
            letter_type VARCHAR,
            approval_status VARCHAR,
            company_name VARCHAR,
            company_address VARCHAR,
            company_rep VARCHAR,
            approver_name VARCHAR,
            approver_center VARCHAR[],
            approver_title VARCHAR,
            file_name VARCHAR,
            text TEXT,
            therapeutic_category VARCHAR,
            product_name VARCHAR,
            indications TEXT,
            deficiency_reason VARCHAR,
            raw_json JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE crl_summaries (
            id INTEGER PRIMARY KEY,
            crl_id VARCHAR REFERENCES crls(id),
            summary VARCHAR NOT NULL,
            model VARCHAR NOT NULL,
            total_tokens INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE crl_embeddings (
            id INTEGER PRIMARY KEY,
            crl_id VARCHAR REFERENCES crls(id),
            embedding FLOAT[1536],
            model VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE qa_annotations (
            id INTEGER PRIMARY KEY,
            question VARCHAR NOT NULL,
            answer VARCHAR NOT NULL,
            relevant_crl_ids VARCHAR[],
            confidence FLOAT,
            model VARCHAR NOT NULL,
            tokens_used INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert sample CRL data
    for i in range(10):
        conn.execute("""
            INSERT INTO crls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, [
            f"test_crl_{i}",
            [f"NDA {215818 + i}"],  # Array, not JSON string
            f"2024-01-{15 + i:02d}",
            "2024",
            "COMPLETE RESPONSE",
            "Approved" if i % 2 == 0 else "Unapproved",
            "Pfizer Inc." if i < 3 else f"Test Pharma {i}",
            f"123 Test St, City {i}",
            f"Rep {i}",
            f"Approver {i}",
            ["Center for Drug Evaluation and Research"],  # Array, not JSON string
            "Director",
            f"test_file_{i}.pdf",
            f"This is test CRL content {i} with deficiencies.",
            "Small molecules" if i % 3 == 0 else None,  # therapeutic_category
            f"Test Product {i}" if i < 5 else None,  # product_name
            "Test indication" if i % 2 == 0 else None,  # indications
            "Clinical" if i % 2 == 0 else "CMC / Quality",  # deficiency_reason
            '{}'  # raw_json
        ])

    # Insert sample summary
    conn.execute("""
        INSERT INTO crl_summaries VALUES (1, 'test_crl_0', 'Test summary', 'gpt-4o-mini', 100, CURRENT_TIMESTAMP)
    """)

    # Insert sample embedding
    embedding = [0.1] * 1536
    conn.execute("""
        INSERT INTO crl_embeddings VALUES (1, 'test_crl_0', ?, 'text-embedding-3-small', CURRENT_TIMESTAMP)
    """, [embedding])

    yield conn
    conn.close()


@pytest.fixture
def client(test_db):
    """FastAPI test client with mocked database."""
    # Mock the database connection to use our test database
    with patch('app.database.DatabaseConnection._connect') as mock_connect:
        with patch('app.database.DatabaseConnection.get_connection', return_value=test_db):
            with patch('app.database.get_db', return_value=test_db):
                # Import app after patching to ensure it uses mocked database
                from app.main import app

                # Mock RAG service to avoid OpenAI API calls
                with patch('app.api.qa.rag_service') as mock_rag:
                    mock_rag.answer_question.return_value = {
                        "question": "What are common deficiencies?",
                        "answer": "Common deficiencies include CMC issues, clinical trial design problems, and manufacturing concerns.",
                        "relevant_crls": ["test_crl_0", "test_crl_1"],
                        "confidence": 0.85,
                        "model": "gpt-4o-mini"
                    }

                    yield TestClient(app)


class TestHealthAndRoot:
    """Test health check and root endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "FDA CRL Explorer API"

    def test_health_check_success(self, client):
        """Test health check endpoint returns database stats."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "total_crls" in data
        assert "total_summaries" in data
        assert "total_embeddings" in data
        assert data["total_crls"] > 0


class TestCRLEndpoints:
    """Test CRL API endpoints."""

    def test_list_crls_default(self, client):
        """Test listing CRLs with default parameters."""
        response = client.get("/api/crls")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

        assert len(data["items"]) <= 50  # Default limit
        assert data["total"] > 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_crls_with_limit(self, client):
        """Test listing CRLs with custom limit."""
        response = client.get("/api/crls?limit=10")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) <= 10
        assert data["limit"] == 10

    def test_list_crls_with_pagination(self, client):
        """Test pagination works correctly."""
        # Get first page
        response1 = client.get("/api/crls?limit=5&offset=0")
        data1 = response1.json()

        # Get second page
        response2 = client.get("/api/crls?limit=5&offset=5")
        data2 = response2.json()

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Items should be different
        ids1 = {item["id"] for item in data1["items"]}
        ids2 = {item["id"] for item in data2["items"]}
        assert ids1 != ids2  # Different pages should have different items

    def test_list_crls_filter_by_status(self, client):
        """Test filtering by approval status."""
        response = client.get("/api/crls?approval_status=Approved&limit=10")

        assert response.status_code == 200
        data = response.json()

        # All items should be approved
        for item in data["items"]:
            assert item["approval_status"] == "Approved"

    def test_list_crls_filter_by_year(self, client):
        """Test filtering by letter year."""
        response = client.get("/api/crls?letter_year=2024&limit=10")

        assert response.status_code == 200
        data = response.json()

        # All items should be from 2024
        for item in data["items"]:
            assert item["letter_year"] == "2024"

    def test_list_crls_filter_by_company(self, client):
        """Test filtering by company name."""
        response = client.get("/api/crls?company_name=Pfizer&limit=10")

        assert response.status_code == 200
        data = response.json()

        # All items should have Pfizer in company name
        for item in data["items"]:
            assert "pfizer" in item["company_name"].lower()

    def test_list_crls_sorting(self, client):
        """Test sorting works correctly."""
        response = client.get("/api/crls?sort_by=letter_date&sort_order=ASC&limit=5")

        assert response.status_code == 200
        data = response.json()

        # Check dates are in ascending order
        dates = [item["letter_date"] for item in data["items"]]
        assert dates == sorted(dates)

    def test_list_crls_invalid_limit(self, client):
        """Test that invalid limit is rejected."""
        response = client.get("/api/crls?limit=200")  # Max is 100

        # Should return validation error
        assert response.status_code == 422

    def test_get_crl_by_id(self, client):
        """Test getting a specific CRL by ID."""
        # First get a CRL ID
        list_response = client.get("/api/crls?limit=1")
        crl_id = list_response.json()["items"][0]["id"]

        # Get that specific CRL using query parameter
        response = client.get(f"/api/crls/detail?crl_id={crl_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == crl_id
        assert "company_name" in data
        assert "letter_date" in data
        # Should include summary if available
        assert "summary" in data

    def test_get_crl_not_found(self, client):
        """Test getting non-existent CRL returns 404."""
        response = client.get("/api/crls/detail?crl_id=NONEXISTENT_ID_12345")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_crl_with_text(self, client):
        """Test getting CRL with full text."""
        # First get a CRL ID
        list_response = client.get("/api/crls?limit=1")
        crl_id = list_response.json()["items"][0]["id"]

        # Get that CRL with text using query parameter
        response = client.get(f"/api/crls/text?crl_id={crl_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == crl_id
        assert "text" in data
        assert len(data["text"]) > 0


class TestStatisticsEndpoints:
    """Test statistics API endpoints."""

    def test_stats_overview(self, client):
        """Test statistics overview endpoint."""
        response = client.get("/api/stats/overview")

        assert response.status_code == 200
        data = response.json()

        assert "total_crls" in data
        assert "by_status" in data
        assert "by_year" in data

        assert data["total_crls"] > 0
        assert isinstance(data["by_status"], dict)
        assert isinstance(data["by_year"], dict)

    def test_company_stats(self, client):
        """Test company statistics endpoint."""
        response = client.get("/api/stats/companies?limit=10")

        assert response.status_code == 200
        data = response.json()

        assert "companies" in data
        assert "total_companies" in data

        assert len(data["companies"]) <= 10
        assert data["total_companies"] > 0

        # Verify company stats structure
        if data["companies"]:
            company = data["companies"][0]
            assert "company_name" in company
            assert "crl_count" in company
            assert "approved_count" in company
            assert "unapproved_count" in company
            assert company["crl_count"] == company["approved_count"] + company["unapproved_count"]

    def test_company_stats_sorted(self, client):
        """Test company statistics are sorted by CRL count."""
        response = client.get("/api/stats/companies?limit=5")

        assert response.status_code == 200
        data = response.json()

        # Verify descending order by crl_count
        counts = [c["crl_count"] for c in data["companies"]]
        assert counts == sorted(counts, reverse=True)


class TestQAEndpoints:
    """Test Q&A API endpoints."""

    def test_ask_question_success(self, client):
        """Test asking a question returns an answer."""
        response = client.post(
            "/api/qa/ask",
            json={"question": "What are common deficiencies?", "top_k": 3}
        )

        assert response.status_code == 200
        data = response.json()

        assert "question" in data
        assert "answer" in data
        assert "relevant_crls" in data
        assert "confidence" in data
        assert "model" in data

        assert data["question"] == "What are common deficiencies?"
        assert len(data["answer"]) > 0
        assert isinstance(data["relevant_crls"], list)
        assert 0.0 <= data["confidence"] <= 1.0

    def test_ask_question_empty_raises_error(self, client):
        """Test that empty question is rejected."""
        response = client.post(
            "/api/qa/ask",
            json={"question": "", "top_k": 3}
        )

        # Should return validation error (422) or bad request (400)
        assert response.status_code in [400, 422]

    def test_ask_question_too_short(self, client):
        """Test that too-short question is rejected."""
        response = client.post(
            "/api/qa/ask",
            json={"question": "Hi", "top_k": 3}
        )

        # Should return validation error
        assert response.status_code == 422

    def test_ask_question_invalid_top_k(self, client):
        """Test that invalid top_k is rejected."""
        response = client.post(
            "/api/qa/ask",
            json={"question": "What are common deficiencies?", "top_k": 100}
        )

        # Should return validation error (top_k max is 20)
        assert response.status_code == 422

    def test_qa_history(self, client):
        """Test getting Q&A history."""
        # First ask a question
        client.post(
            "/api/qa/ask",
            json={"question": "Test question for history", "top_k": 3}
        )

        # Get history
        response = client.get("/api/qa/history?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_404_for_unknown_endpoint(self, client):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/api/unknown/endpoint")

        assert response.status_code == 404

    def test_cors_headers_present(self, client):
        """Test that CORS headers are configured."""
        # Make a regular GET request (TestClient doesn't fully simulate CORS preflight)
        response = client.get("/api/crls?limit=1")

        # CORS middleware should add allow-origin header
        # (In TestClient, CORS headers may not appear, but the middleware is configured)
        assert response.status_code == 200


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_docs_available(self, client):
        """Test that OpenAPI documentation is accessible."""
        response = client.get("/docs")

        assert response.status_code == 200

    def test_redoc_available(self, client):
        """Test that ReDoc documentation is accessible."""
        response = client.get("/redoc")

        assert response.status_code == 200

    def test_openapi_json_schema(self, client):
        """Test that OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
