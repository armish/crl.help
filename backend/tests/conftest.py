"""
Pytest configuration and shared fixtures for FDA CRL Explorer tests.

This file contains:
- Test fixtures for database connections
- Mock factories for test data
- Common test utilities
"""

import os
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
import duckdb


@pytest.fixture(scope="session")
def test_env_vars():
    """
    Fixture to set up test environment variables.

    This fixture sets required environment variables for testing
    and cleans them up after tests complete.
    """
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"
    os.environ["DATABASE_PATH"] = ":memory:"  # In-memory database for tests
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="function")
def temp_db_path() -> Generator[str, None, None]:
    """
    Fixture that provides a temporary database file path.

    Creates a temporary file for the database and cleans it up after the test.

    Yields:
        str: Path to temporary database file
    """
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def test_db_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Fixture that provides an in-memory DuckDB connection for testing.

    Yields:
        duckdb.DuckDBPyConnection: Database connection
    """
    conn = duckdb.connect(":memory:")

    yield conn

    conn.close()


@pytest.fixture(scope="function")
def mock_openai_client(mocker):
    """
    Fixture that provides a mocked OpenAI client.

    This prevents actual API calls during testing.

    Returns:
        MagicMock: Mocked OpenAI client
    """
    mock_client = MagicMock()

    # Mock chat completions
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "Test summary"
    mock_completion.usage.total_tokens = 100
    mock_client.chat.completions.create.return_value = mock_completion

    # Mock embeddings
    mock_embedding = MagicMock()
    mock_embedding.data = [MagicMock()]
    mock_embedding.data[0].embedding = [0.1] * 1536  # 1536 dimensions
    mock_embedding.usage.total_tokens = 50
    mock_client.embeddings.create.return_value = mock_embedding

    return mock_client


@pytest.fixture(scope="function")
def sample_crl_data():
    """
    Fixture that provides sample CRL data for testing.

    Returns:
        dict: Sample CRL data matching the expected structure
    """
    return {
        "application_number": ["NDA 215818"],
        "letter_date": "01/15/2024",
        "letter_year": "2024",
        "letter_type": "COMPLETE RESPONSE",
        "approval_status": "Unapproved",
        "company_name": "Test Pharmaceutical Inc.",
        "company_address": "123 Test St, Test City, TS 12345",
        "company_rep": "John Doe",
        "approver_name": "Jane Smith",
        "approver_center": ["Center for Drug Evaluation and Research"],
        "approver_title": "Director, Division of Drug Evaluation",
        "file_name": "test_crl_2024.pdf",
        "text": "Dear Applicant: We have completed our review of your application... [deficiencies listed]"
    }


@pytest.fixture(scope="function")
def sample_crl_list():
    """
    Fixture that provides a list of sample CRL data for testing.

    Returns:
        list: List of sample CRL dictionaries
    """
    base_data = {
        "application_number": ["NDA 000000"],
        "letter_type": "COMPLETE RESPONSE",
        "company_address": "123 Test St, Test City, TS 12345",
        "company_rep": "John Doe",
        "approver_name": "Jane Smith",
        "approver_center": ["Center for Drug Evaluation and Research"],
        "approver_title": "Director, Division of Drug Evaluation",
        "file_name": "test_crl.pdf",
        "text": "Dear Applicant: We have completed our review..."
    }

    crls = []
    for i in range(5):
        crl = base_data.copy()
        crl["application_number"] = [f"NDA {215818 + i}"]
        crl["letter_date"] = f"01/{15 + i}/2024"
        crl["letter_year"] = "2024"
        crl["approval_status"] = "Approved" if i % 2 == 0 else "Unapproved"
        crl["company_name"] = f"Test Pharmaceutical {i} Inc."
        crls.append(crl)

    return crls


@pytest.fixture(scope="function", autouse=True)
def reset_db_singleton():
    """Reset the DatabaseConnection singleton between tests."""
    from app.database import DatabaseConnection
    # Reset the singleton
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None
    yield
    # Clean up after test
    if DatabaseConnection._connection is not None:
        try:
            DatabaseConnection._connection.close()
        except:
            pass
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None


@pytest.fixture(scope="function")
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

    conn.execute("""
        CREATE TABLE processing_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
def client(test_db, test_env_vars):
    """FastAPI test client with mocked database."""
    import sys
    from app.main import app
    from fastapi.testclient import TestClient

    # Patch get_db where it's used (in main.py) to return our test database
    with patch('app.main.get_db', return_value=test_db):
        # Get module references from sys.modules to avoid creating new references in local scope
        # This prevents the modules from being visible to DuckDB's replacement scan
        crls_module = sys.modules.get('app.api.crls')
        export_module = sys.modules.get('app.api.export')
        stats_module = sys.modules.get('app.api.stats')
        qa_module = sys.modules.get('app.api.qa')

        patches = []
        if crls_module:
            patches.extend([
                patch.object(crls_module.crl_repo, 'conn', test_db),
                patch.object(crls_module.summary_repo, 'conn', test_db),
            ])
        if export_module:
            patches.extend([
                patch.object(export_module.crl_repo, 'conn', test_db),
                patch.object(export_module.summary_repo, 'conn', test_db),
            ])
        if stats_module:
            patches.append(patch.object(stats_module.crl_repo, 'conn', test_db))
        if qa_module:
            patches.append(patch.object(qa_module.qa_repo, 'conn', test_db))

        # Apply all patches
        if patches:
            with patches[0], patches[1], patches[2] if len(patches) > 2 else patch('unittest.mock.MagicMock'), \
                 patches[3] if len(patches) > 3 else patch('unittest.mock.MagicMock'), \
                 patches[4] if len(patches) > 4 else patch('unittest.mock.MagicMock'), \
                 patches[5] if len(patches) > 5 else patch('unittest.mock.MagicMock'):
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
        else:
            # Fallback if modules aren't loaded yet
            with patch('app.api.qa.rag_service') as mock_rag:
                mock_rag.answer_question.return_value = {
                    "question": "What are common deficiencies?",
                    "answer": "Common deficiencies include CMC issues, clinical trial design problems, and manufacturing concerns.",
                    "relevant_crls": ["test_crl_0", "test_crl_1"],
                    "confidence": 0.85,
                    "model": "gpt-4o-mini"
                }

                yield TestClient(app)


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """
    Fixture to reset the settings cache between tests.

    The get_settings function uses lru_cache, so we need to clear it
    between tests to ensure a fresh settings instance.
    """
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
