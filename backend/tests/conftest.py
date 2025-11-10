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
from unittest.mock import MagicMock

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
