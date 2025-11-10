"""
Tests for database schema definitions.

Tests the SQL schema creation statements and schema utility functions.
"""

import pytest
from app.schemas import (
    CREATE_CRLS_TABLE,
    CREATE_SUMMARIES_TABLE,
    CREATE_EMBEDDINGS_TABLE,
    CREATE_QA_TABLE,
    CREATE_METADATA_TABLE,
    CREATE_INDEXES,
    ALL_TABLES,
    get_init_schema_sql,
)


class TestSchemaConstants:
    """Test schema constant definitions."""

    def test_create_crls_table_exists(self):
        """Test that CRLs table creation SQL is defined."""
        assert CREATE_CRLS_TABLE is not None
        assert "CREATE TABLE IF NOT EXISTS crls" in CREATE_CRLS_TABLE
        assert "id VARCHAR PRIMARY KEY" in CREATE_CRLS_TABLE

    def test_create_summaries_table_exists(self):
        """Test that summaries table creation SQL is defined."""
        assert CREATE_SUMMARIES_TABLE is not None
        assert "CREATE TABLE IF NOT EXISTS crl_summaries" in CREATE_SUMMARIES_TABLE
        assert "crl_id VARCHAR" in CREATE_SUMMARIES_TABLE

    def test_create_embeddings_table_exists(self):
        """Test that embeddings table creation SQL is defined."""
        assert CREATE_EMBEDDINGS_TABLE is not None
        assert "CREATE TABLE IF NOT EXISTS crl_embeddings" in CREATE_EMBEDDINGS_TABLE
        assert "embedding FLOAT[]" in CREATE_EMBEDDINGS_TABLE

    def test_create_qa_table_exists(self):
        """Test that Q&A table creation SQL is defined."""
        assert CREATE_QA_TABLE is not None
        assert "CREATE TABLE IF NOT EXISTS qa_annotations" in CREATE_QA_TABLE
        assert "question TEXT" in CREATE_QA_TABLE

    def test_create_metadata_table_exists(self):
        """Test that metadata table creation SQL is defined."""
        assert CREATE_METADATA_TABLE is not None
        assert "CREATE TABLE IF NOT EXISTS processing_metadata" in CREATE_METADATA_TABLE
        assert "key VARCHAR PRIMARY KEY" in CREATE_METADATA_TABLE

    def test_create_indexes_is_list(self):
        """Test that CREATE_INDEXES is a list of index creation statements."""
        assert isinstance(CREATE_INDEXES, list)
        assert len(CREATE_INDEXES) > 0
        for index_sql in CREATE_INDEXES:
            assert "CREATE INDEX IF NOT EXISTS" in index_sql

    def test_all_tables_contains_all_tables(self):
        """Test that ALL_TABLES contains all table creation statements."""
        assert isinstance(ALL_TABLES, list)
        assert len(ALL_TABLES) == 5  # 5 tables total
        assert CREATE_CRLS_TABLE in ALL_TABLES
        assert CREATE_SUMMARIES_TABLE in ALL_TABLES
        assert CREATE_EMBEDDINGS_TABLE in ALL_TABLES
        assert CREATE_QA_TABLE in ALL_TABLES
        assert CREATE_METADATA_TABLE in ALL_TABLES


class TestGetInitSchemaSql:
    """Test the get_init_schema_sql function."""

    def test_get_init_schema_sql_returns_string(self):
        """Test that get_init_schema_sql returns a string."""
        result = get_init_schema_sql()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_init_schema_sql_contains_all_tables(self):
        """Test that the returned SQL contains all table creation statements."""
        result = get_init_schema_sql()

        # Check for all table creation statements
        assert "CREATE TABLE IF NOT EXISTS crls" in result
        assert "CREATE TABLE IF NOT EXISTS crl_summaries" in result
        assert "CREATE TABLE IF NOT EXISTS crl_embeddings" in result
        assert "CREATE TABLE IF NOT EXISTS qa_annotations" in result
        assert "CREATE TABLE IF NOT EXISTS processing_metadata" in result

    def test_get_init_schema_sql_contains_indexes(self):
        """Test that the returned SQL contains index creation statements."""
        result = get_init_schema_sql()

        # Check for some index creation statements
        assert "CREATE INDEX IF NOT EXISTS idx_crls_approval_status" in result
        assert "CREATE INDEX IF NOT EXISTS idx_crls_letter_year" in result
        assert "CREATE INDEX IF NOT EXISTS idx_summaries_crl_id" in result
        assert "CREATE INDEX IF NOT EXISTS idx_embeddings_crl_id" in result

    def test_get_init_schema_sql_properly_formatted(self):
        """Test that the SQL is properly formatted with newlines."""
        result = get_init_schema_sql()

        # Should have multiple statements separated by double newlines
        statements = result.split("\n\n")
        # 5 tables + multiple indexes
        assert len(statements) >= 5

    def test_get_init_schema_sql_order(self):
        """Test that tables are defined before indexes."""
        result = get_init_schema_sql()

        # Find position of first CREATE TABLE and first CREATE INDEX
        first_table_pos = result.find("CREATE TABLE")
        first_index_pos = result.find("CREATE INDEX")

        # Tables should come before indexes
        assert first_table_pos < first_index_pos
