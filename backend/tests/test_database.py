"""
Unit tests for app/database.py

Tests database connection management, schema initialization,
and all repository classes (CRUD operations).
"""

import pytest
import duckdb
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.database import (
    DatabaseConnection,
    get_db,
    init_db,
    CRLRepository,
    SummaryRepository,
    EmbeddingRepository,
    QARepository,
    MetadataRepository,
)


# ============================================================================
# DatabaseConnection Tests
# ============================================================================


class TestDatabaseConnection:
    """Test cases for DatabaseConnection singleton class."""

    def test_singleton_pattern(self, test_env_vars):
        """Test that DatabaseConnection implements singleton pattern."""
        db1 = DatabaseConnection()
        db2 = DatabaseConnection()

        # Should return the same instance
        assert db1 is db2

    def test_get_connection(self, test_env_vars):
        """Test getting database connection."""
        db = DatabaseConnection()
        conn = db.get_connection()

        assert conn is not None
        assert isinstance(conn, duckdb.DuckDBPyConnection)

    def test_connection_not_initialized_error(self):
        """Test that error is raised if connection not initialized."""
        # Reset singleton instance
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        db = DatabaseConnection.__new__(DatabaseConnection)

        with pytest.raises(RuntimeError, match="Database connection not initialized"):
            db.get_connection()

        # Reinitialize for cleanup
        DatabaseConnection()


# ============================================================================
# Schema Initialization Tests
# ============================================================================


class TestSchemaInitialization:
    """Test cases for database schema initialization."""

    def test_init_db_creates_tables(self, test_env_vars):
        """Test that init_db creates all required tables."""
        init_db()
        conn = get_db()

        # Check that all tables exist
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = [t[0] for t in tables]

        expected_tables = [
            "crls",
            "crl_summaries",
            "crl_embeddings",
            "qa_annotations",
            "processing_metadata",
        ]

        for table in expected_tables:
            assert table in table_names, f"Table {table} not created"

    def test_init_db_creates_indexes(self, test_env_vars):
        """Test that init_db creates indexes."""
        init_db()
        conn = get_db()

        # Check that indexes exist
        indexes = conn.execute(
            "SELECT index_name FROM duckdb_indexes()"
        ).fetchall()
        index_names = [i[0] for i in indexes]

        # At least some indexes should be created
        expected_indexes = [
            "idx_crls_approval_status",
            "idx_crls_letter_year",
            "idx_crls_company_name",
            "idx_crls_letter_date",
        ]

        for index in expected_indexes:
            assert index in index_names, f"Index {index} not created"

    def test_init_db_idempotent(self, test_env_vars):
        """Test that init_db can be called multiple times safely."""
        # Should not raise an error when called multiple times
        init_db()
        init_db()
        init_db()

        conn = get_db()
        # Check tables still exist
        tables = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchone()[0]
        assert tables >= 5


# ============================================================================
# CRLRepository Tests
# ============================================================================


@pytest.mark.database
class TestCRLRepository:
    """Test cases for CRLRepository class."""

    @pytest.fixture(autouse=True)
    def setup(self, test_env_vars):
        """Set up test database for each test."""
        # Reset the database connection singleton to get a fresh in-memory DB
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        init_db()
        self.repo = CRLRepository()

    def test_create_crl(self, sample_crl_data):
        """Test creating a new CRL."""
        crl_id = "NDA215818_20240115"
        crl_data = {
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {"test": "data"},
        }

        result = self.repo.create(crl_data)

        assert result == crl_id

        # Verify it was inserted
        saved_crl = self.repo.get_by_id(crl_id)
        assert saved_crl is not None
        assert saved_crl["id"] == crl_id
        assert saved_crl["company_name"] == sample_crl_data["company_name"]

    def test_get_by_id_existing(self, sample_crl_data):
        """Test getting CRL by ID that exists."""
        crl_id = "NDA215818_20240115"
        crl_data = {
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        }
        self.repo.create(crl_data)

        result = self.repo.get_by_id(crl_id)

        assert result is not None
        assert result["id"] == crl_id
        assert result["company_name"] == sample_crl_data["company_name"]
        assert result["approval_status"] == sample_crl_data["approval_status"]

    def test_get_by_id_nonexistent(self):
        """Test getting CRL by ID that doesn't exist."""
        result = self.repo.get_by_id("nonexistent_id")
        assert result is None

    def test_exists_true(self, sample_crl_data):
        """Test exists returns True for existing CRL."""
        crl_id = "NDA215818_20240115"
        crl_data = {
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        }
        self.repo.create(crl_data)

        assert self.repo.exists(crl_id) is True

    def test_exists_false(self):
        """Test exists returns False for non-existing CRL."""
        assert self.repo.exists("nonexistent_id") is False

    def test_update_existing_crl(self, sample_crl_data):
        """Test updating an existing CRL."""
        crl_id = "NDA215818_20240115"
        crl_data = {
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        }
        self.repo.create(crl_data)

        # Update the CRL
        updated_data = {
            **crl_data,
            "company_name": "Updated Pharmaceutical Inc.",
            "approval_status": "Approved",
        }
        result = self.repo.update(crl_id, updated_data)

        assert result is True

        # Verify the update
        saved_crl = self.repo.get_by_id(crl_id)
        assert saved_crl["company_name"] == "Updated Pharmaceutical Inc."
        assert saved_crl["approval_status"] == "Approved"

    def test_update_nonexistent_crl(self, sample_crl_data):
        """Test updating a non-existing CRL returns False."""
        crl_data = {
            "id": "nonexistent_id",
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        }

        result = self.repo.update("nonexistent_id", crl_data)
        assert result is False

    def test_get_all_no_filters(self, sample_crl_list):
        """Test getting all CRLs without filters."""
        # Insert sample CRLs
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_20240115"
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": "2024-01-15",
                "raw_json": {},
            })

        crls, total = self.repo.get_all(limit=10, offset=0)

        assert len(crls) == 5
        assert total == 5

    def test_get_all_with_approval_status_filter(self, sample_crl_list):
        """Test filtering CRLs by approval status."""
        # Insert sample CRLs
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_20240115"
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": "2024-01-15",
                "raw_json": {},
            })

        crls, total = self.repo.get_all(approval_status=["Approved"])

        # sample_crl_list has alternating status (even indices are Approved)
        assert total == 3  # indices 0, 2, 4
        for crl in crls:
            assert crl["approval_status"] == "Approved"

    def test_get_all_with_year_filter(self, sample_crl_list):
        """Test filtering CRLs by year."""
        # Insert sample CRLs with different years
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_2024"
            year = "2024" if i < 3 else "2023"
            crl["letter_year"] = year
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": f"{year}-01-15",
                "raw_json": {},
            })

        crls, total = self.repo.get_all(letter_year=["2024"])

        assert total == 3
        for crl in crls:
            assert crl["letter_year"] == "2024"

    def test_get_all_with_company_name_filter(self, sample_crl_list):
        """Test filtering CRLs by company name (partial match)."""
        # Insert sample CRLs
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_20240115"
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": "2024-01-15",
                "raw_json": {},
            })

        # Search for "Pharmaceutical 2"
        crls, total = self.repo.get_all(company_name="Pharmaceutical 2")

        assert total == 1
        assert "Pharmaceutical 2" in crls[0]["company_name"]

    def test_get_all_with_search_text(self, sample_crl_list):
        """Test full-text search in CRL text."""
        # Insert sample CRLs with unique text
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_20240115"
            crl["text"] = f"Standard text. Unique word: unicorn{i}"
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": "2024-01-15",
                "raw_json": {},
            })

        crls, total = self.repo.get_all(search_text="unicorn2")

        assert total == 1
        assert "unicorn2" in crls[0]["text"]

    def test_get_all_pagination(self, sample_crl_list):
        """Test pagination of CRLs."""
        # Insert sample CRLs
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_20240115"
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": "2024-01-15",
                "raw_json": {},
            })

        # Get first page
        crls_page1, total1 = self.repo.get_all(limit=2, offset=0)
        assert len(crls_page1) == 2
        assert total1 == 5

        # Get second page
        crls_page2, total2 = self.repo.get_all(limit=2, offset=2)
        assert len(crls_page2) == 2
        assert total2 == 5

        # Verify different results
        assert crls_page1[0]["id"] != crls_page2[0]["id"]

    def test_get_all_sorting(self, sample_crl_list):
        """Test sorting CRLs."""
        # Insert sample CRLs with different dates
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_2024011{i}"
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": f"2024-01-1{i+1}",
                "raw_json": {},
            })

        # Sort ascending by date
        crls_asc, _ = self.repo.get_all(sort_by="letter_date", sort_order="ASC")
        assert crls_asc[0]["letter_date"] < crls_asc[-1]["letter_date"]

        # Sort descending by date
        crls_desc, _ = self.repo.get_all(sort_by="letter_date", sort_order="DESC")
        assert crls_desc[0]["letter_date"] > crls_desc[-1]["letter_date"]

    def test_get_stats_empty_database(self):
        """Test getting stats from empty database."""
        stats = self.repo.get_stats()

        assert stats["total_crls"] == 0
        assert stats["by_status"] == {}
        assert stats["by_year"] == {}

    def test_get_stats_with_data(self, sample_crl_list):
        """Test getting statistics with data."""
        # Insert sample CRLs
        for i, crl in enumerate(sample_crl_list):
            crl_id = f"NDA{215818 + i}_20240115"
            self.repo.create({
                "id": crl_id,
                **crl,
                "letter_date": "2024-01-15",
                "raw_json": {},
            })

        stats = self.repo.get_stats()

        assert stats["total_crls"] == 5
        assert stats["by_status"]["Approved"] == 3  # indices 0, 2, 4
        assert stats["by_status"]["Unapproved"] == 2  # indices 1, 3
        assert stats["by_year"]["2024"] == 5


# ============================================================================
# SummaryRepository Tests
# ============================================================================


@pytest.mark.database
class TestSummaryRepository:
    """Test cases for SummaryRepository class."""

    @pytest.fixture(autouse=True)
    def setup(self, test_env_vars):
        """Set up test database for each test."""
        # Reset the database connection singleton to get a fresh in-memory DB
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        init_db()
        self.repo = SummaryRepository()
        self.crl_repo = CRLRepository()

    def test_create_summary(self, sample_crl_data):
        """Test creating a new summary."""
        # First create a CRL
        crl_id = "NDA215818_20240115"
        self.crl_repo.create({
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        })

        # Create summary
        summary_id = f"summary_{crl_id}"
        summary_data = {
            "id": summary_id,
            "crl_id": crl_id,
            "summary": "This is a test summary of the CRL.",
            "model": "gpt-4o-mini",
            "tokens_used": 150,
        }

        result = self.repo.create(summary_data)

        assert result == summary_id

        # Verify it was inserted
        saved_summary = self.repo.get_by_crl_id(crl_id)
        assert saved_summary is not None
        assert saved_summary["summary"] == "This is a test summary of the CRL."

    def test_get_by_crl_id_existing(self, sample_crl_data):
        """Test getting summary by CRL ID that exists."""
        crl_id = "NDA215818_20240115"
        self.crl_repo.create({
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        })

        summary_id = f"summary_{crl_id}"
        self.repo.create({
            "id": summary_id,
            "crl_id": crl_id,
            "summary": "Test summary",
            "model": "gpt-4o-mini",
            "tokens_used": 100,
        })

        result = self.repo.get_by_crl_id(crl_id)

        assert result is not None
        assert result["crl_id"] == crl_id
        assert result["model"] == "gpt-4o-mini"

    def test_get_by_crl_id_nonexistent(self):
        """Test getting summary for non-existing CRL."""
        result = self.repo.get_by_crl_id("nonexistent_crl")
        assert result is None

    def test_exists_true(self, sample_crl_data):
        """Test exists returns True for existing summary."""
        crl_id = "NDA215818_20240115"
        self.crl_repo.create({
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        })

        summary_id = f"summary_{crl_id}"
        self.repo.create({
            "id": summary_id,
            "crl_id": crl_id,
            "summary": "Test summary",
            "model": "gpt-4o-mini",
        })

        assert self.repo.exists(crl_id) is True

    def test_exists_false(self):
        """Test exists returns False for non-existing summary."""
        assert self.repo.exists("nonexistent_crl") is False


# ============================================================================
# EmbeddingRepository Tests
# ============================================================================


@pytest.mark.database
class TestEmbeddingRepository:
    """Test cases for EmbeddingRepository class."""

    @pytest.fixture(autouse=True)
    def setup(self, test_env_vars):
        """Set up test database for each test."""
        # Reset the database connection singleton to get a fresh in-memory DB
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        init_db()
        self.repo = EmbeddingRepository()
        self.crl_repo = CRLRepository()

    def test_create_embedding(self, sample_crl_data):
        """Test creating a new embedding."""
        # First create a CRL
        crl_id = "NDA215818_20240115"
        self.crl_repo.create({
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        })

        # Create embedding
        embedding_id = f"emb_{crl_id}"
        embedding_data = {
            "id": embedding_id,
            "crl_id": crl_id,
            "embedding_type": "summary",
            "embedding": [0.1, 0.2, 0.3] * 512,  # 1536 dimensions
            "model": "text-embedding-3-small",
        }

        result = self.repo.create(embedding_data)

        assert result == embedding_id

        # Verify it was inserted
        saved_embedding = self.repo.get_by_crl_id(crl_id, "summary")
        assert saved_embedding is not None
        assert saved_embedding["embedding_type"] == "summary"

    def test_get_by_crl_id_existing(self, sample_crl_data):
        """Test getting embedding by CRL ID that exists."""
        crl_id = "NDA215818_20240115"
        self.crl_repo.create({
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        })

        embedding_id = f"emb_{crl_id}"
        self.repo.create({
            "id": embedding_id,
            "crl_id": crl_id,
            "embedding_type": "summary",
            "embedding": [0.1] * 1536,
            "model": "text-embedding-3-small",
        })

        result = self.repo.get_by_crl_id(crl_id, "summary")

        assert result is not None
        assert result["crl_id"] == crl_id
        assert result["model"] == "text-embedding-3-small"
        assert len(result["embedding"]) == 1536

    def test_get_by_crl_id_nonexistent(self):
        """Test getting embedding for non-existing CRL."""
        result = self.repo.get_by_crl_id("nonexistent_crl")
        assert result is None

    def test_get_all_embeddings(self, sample_crl_list):
        """Test getting all embeddings of a specific type."""
        # Create multiple CRLs with embeddings
        for i, crl in enumerate(sample_crl_list[:3]):
            crl_id = f"NDA{215818 + i}_20240115"
            self.crl_repo.create({
                "id": crl_id,
                **crl,
                "letter_date": "2024-01-15",
                "raw_json": {},
            })

            self.repo.create({
                "id": f"emb_{crl_id}",
                "crl_id": crl_id,
                "embedding_type": "summary",
                "embedding": [0.1 * i] * 1536,
                "model": "text-embedding-3-small",
            })

        embeddings = self.repo.get_all_embeddings("summary")

        assert len(embeddings) == 3
        for emb in embeddings:
            assert emb["embedding_type"] == "summary"

    def test_exists_true(self, sample_crl_data):
        """Test exists returns True for existing embedding."""
        crl_id = "NDA215818_20240115"
        self.crl_repo.create({
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        })

        self.repo.create({
            "id": f"emb_{crl_id}",
            "crl_id": crl_id,
            "embedding_type": "summary",
            "embedding": [0.1] * 1536,
            "model": "text-embedding-3-small",
        })

        assert self.repo.exists(crl_id, "summary") is True

    def test_exists_false(self):
        """Test exists returns False for non-existing embedding."""
        assert self.repo.exists("nonexistent_crl", "summary") is False

    def test_different_embedding_types(self, sample_crl_data):
        """Test handling different embedding types for same CRL."""
        crl_id = "NDA215818_20240115"
        self.crl_repo.create({
            "id": crl_id,
            **sample_crl_data,
            "letter_date": "2024-01-15",
            "raw_json": {},
        })

        # Create both summary and full_text embeddings
        self.repo.create({
            "id": f"emb_summary_{crl_id}",
            "crl_id": crl_id,
            "embedding_type": "summary",
            "embedding": [0.1] * 1536,
            "model": "text-embedding-3-small",
        })

        self.repo.create({
            "id": f"emb_full_{crl_id}",
            "crl_id": crl_id,
            "embedding_type": "full_text",
            "embedding": [0.2] * 1536,
            "model": "text-embedding-3-small",
        })

        # Both should exist
        assert self.repo.exists(crl_id, "summary") is True
        assert self.repo.exists(crl_id, "full_text") is True

        # Should be able to retrieve both
        summary_emb = self.repo.get_by_crl_id(crl_id, "summary")
        full_emb = self.repo.get_by_crl_id(crl_id, "full_text")

        assert summary_emb["embedding_type"] == "summary"
        assert full_emb["embedding_type"] == "full_text"


# ============================================================================
# QARepository Tests
# ============================================================================


@pytest.mark.database
class TestQARepository:
    """Test cases for QARepository class."""

    @pytest.fixture(autouse=True)
    def setup(self, test_env_vars):
        """Set up test database for each test."""
        # Reset the database connection singleton to get a fresh in-memory DB
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        init_db()
        self.repo = QARepository()

    def test_create_qa(self):
        """Test creating a new Q&A record."""
        qa_id = "qa_001"
        qa_data = {
            "id": qa_id,
            "question": "What are the common deficiencies?",
            "answer": "The common deficiencies include...",
            "relevant_crl_ids": ["NDA215818_20240115", "NDA215819_20240116"],
            "model": "gpt-4o-mini",
            "tokens_used": 250,
        }

        result = self.repo.create(qa_data)

        assert result == qa_id

        # Verify it was inserted
        recent_qa = self.repo.get_recent(limit=1)
        assert len(recent_qa) == 1
        assert recent_qa[0]["question"] == "What are the common deficiencies?"

    def test_get_recent_empty(self):
        """Test getting recent Q&A from empty database."""
        result = self.repo.get_recent(limit=10)
        assert result == []

    def test_get_recent_with_data(self):
        """Test getting recent Q&A records."""
        import time

        # Create multiple Q&A records with small delays to ensure different timestamps
        for i in range(5):
            self.repo.create({
                "id": f"qa_{i:03d}",
                "question": f"Question {i}?",
                "answer": f"Answer {i}.",
                "relevant_crl_ids": [],
                "model": "gpt-4o-mini",
                "tokens_used": 100,
            })
            # Small delay to ensure different timestamps
            time.sleep(0.01)

        recent_qa = self.repo.get_recent(limit=3)

        assert len(recent_qa) == 3
        # Should be ordered by created_at DESC (most recent first)
        # The most recent should be qa_004
        assert recent_qa[0]["id"] == "qa_004"
        # All returned IDs should be from the ones we created
        returned_ids = {qa["id"] for qa in recent_qa}
        assert returned_ids.issubset({"qa_000", "qa_001", "qa_002", "qa_003", "qa_004"})

    def test_get_recent_limit(self):
        """Test that limit parameter works correctly."""
        # Create 10 Q&A records
        for i in range(10):
            self.repo.create({
                "id": f"qa_{i:03d}",
                "question": f"Question {i}?",
                "answer": f"Answer {i}.",
                "relevant_crl_ids": [],
                "model": "gpt-4o-mini",
            })

        recent_qa = self.repo.get_recent(limit=5)

        assert len(recent_qa) == 5


# ============================================================================
# MetadataRepository Tests
# ============================================================================


@pytest.mark.database
class TestMetadataRepository:
    """Test cases for MetadataRepository class."""

    @pytest.fixture(autouse=True)
    def setup(self, test_env_vars):
        """Set up test database for each test."""
        # Reset the database connection singleton to get a fresh in-memory DB
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        init_db()
        self.repo = MetadataRepository()

    def test_set_new_key(self):
        """Test setting a new metadata key."""
        self.repo.set("last_download_date", "2024-01-15")

        result = self.repo.get("last_download_date")
        assert result == "2024-01-15"

    def test_set_update_existing_key(self):
        """Test updating an existing metadata key."""
        self.repo.set("last_download_date", "2024-01-15")
        self.repo.set("last_download_date", "2024-01-16")

        result = self.repo.get("last_download_date")
        assert result == "2024-01-16"

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        result = self.repo.get("nonexistent_key")
        assert result is None

    def test_set_multiple_keys(self):
        """Test setting multiple metadata keys."""
        self.repo.set("last_download_date", "2024-01-15")
        self.repo.set("total_crls_processed", "392")
        self.repo.set("last_processing_date", "2024-01-16")

        assert self.repo.get("last_download_date") == "2024-01-15"
        assert self.repo.get("total_crls_processed") == "392"
        assert self.repo.get("last_processing_date") == "2024-01-16"
