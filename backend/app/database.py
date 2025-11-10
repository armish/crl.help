"""
Database connection management and repository classes for FDA CRL Explorer.
Provides DuckDB connection handling and CRUD operations via repository pattern.
"""

import duckdb
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

from app.config import settings
from app.schemas import ALL_TABLES, CREATE_INDEXES
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseConnection:
    """
    Singleton database connection manager for DuckDB.

    Ensures only one connection instance is created and shared across
    the application lifecycle.
    """

    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[duckdb.DuckDBPyConnection] = None

    def __new__(cls):
        """Create or return existing singleton instance."""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database connection if not already initialized."""
        if self._connection is None:
            self._connect()

    def _connect(self) -> None:
        """Establish connection to DuckDB database."""
        try:
            # Ensure data directory exists
            db_path = Path(settings.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to DuckDB
            self._connection = duckdb.connect(
                database=str(db_path),
                read_only=False
            )

            logger.info(f"Connected to DuckDB database at {settings.database_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Get the database connection.

        Returns:
            duckdb.DuckDBPyConnection: Active database connection

        Raises:
            RuntimeError: If connection is not initialized
        """
        if self._connection is None:
            raise RuntimeError("Database connection not initialized")
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")


def get_db() -> duckdb.DuckDBPyConnection:
    """
    Get database connection instance.

    Returns:
        duckdb.DuckDBPyConnection: Database connection
    """
    db = DatabaseConnection()
    return db.get_connection()


def init_db() -> None:
    """
    Initialize database schema.

    Creates all tables and indexes if they don't exist.
    This function is idempotent and safe to call multiple times.
    """
    logger.info("Initializing database schema...")

    conn = get_db()

    try:
        # Create tables
        for table_sql in ALL_TABLES:
            conn.execute(table_sql)
            logger.debug(f"Executed table creation SQL")

        # Create indexes
        for index_sql in CREATE_INDEXES:
            conn.execute(index_sql)
            logger.debug(f"Executed index creation SQL")

        logger.info("Database schema initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# ============================================================================
# Repository Classes
# ============================================================================


class CRLRepository:
    """Repository for CRL (Complete Response Letter) operations."""

    def __init__(self):
        self.conn = get_db()

    def create(self, crl_data: Dict[str, Any]) -> str:
        """
        Create a new CRL record.

        Args:
            crl_data: Dictionary containing CRL data

        Returns:
            str: ID of created CRL

        Example:
            >>> repo = CRLRepository()
            >>> crl_id = repo.create({
            ...     "id": "NDA215818_20250425",
            ...     "application_number": ["NDA 215818"],
            ...     "letter_date": "2025-04-25",
            ...     ...
            ... })
        """
        # Convert arrays and JSON to proper format
        raw_json = json.dumps(crl_data.get("raw_json", {}))

        query = """
        INSERT INTO crls (
            id, application_number, letter_date, letter_year, letter_type,
            approval_status, company_name, company_address, company_rep,
            approver_name, approver_center, approver_title, file_name,
            text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::JSON)
        """

        self.conn.execute(query, [
            crl_data["id"],
            crl_data.get("application_number", []),
            crl_data.get("letter_date"),
            crl_data.get("letter_year"),
            crl_data.get("letter_type"),
            crl_data.get("approval_status"),
            crl_data.get("company_name"),
            crl_data.get("company_address"),
            crl_data.get("company_rep"),
            crl_data.get("approver_name"),
            crl_data.get("approver_center", []),
            crl_data.get("approver_title"),
            crl_data.get("file_name"),
            crl_data.get("text"),
            raw_json,
        ])

        logger.debug(f"Created CRL: {crl_data['id']}")
        return crl_data["id"]

    def get_by_id(self, crl_id: str) -> Optional[Dict[str, Any]]:
        """
        Get CRL by ID.

        Args:
            crl_id: CRL identifier

        Returns:
            Optional[Dict]: CRL data or None if not found
        """
        result = self.conn.execute(
            "SELECT * FROM crls WHERE id = ?",
            [crl_id]
        ).fetchone()

        if result:
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        return None

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        approval_status: Optional[str] = None,
        letter_year: Optional[str] = None,
        company_name: Optional[str] = None,
        search_text: Optional[str] = None,
        sort_by: str = "letter_date",
        sort_order: str = "DESC"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get CRLs with filtering, sorting, and pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            approval_status: Filter by approval status
            letter_year: Filter by year
            company_name: Filter by company name (partial match)
            search_text: Full-text search in text field
            sort_by: Column to sort by
            sort_order: Sort direction (ASC or DESC)

        Returns:
            Tuple[List[Dict], int]: (List of CRLs, total count)
        """
        # Build WHERE clause
        where_clauses = []
        params = []

        if approval_status:
            where_clauses.append("approval_status = ?")
            params.append(approval_status)

        if letter_year:
            where_clauses.append("letter_year = ?")
            params.append(letter_year)

        if company_name:
            where_clauses.append("company_name ILIKE ?")
            params.append(f"%{company_name}%")

        if search_text:
            where_clauses.append("text ILIKE ?")
            params.append(f"%{search_text}%")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM crls WHERE {where_clause}"
        total_count = self.conn.execute(count_query, params).fetchone()[0]

        # Get paginated results
        query = f"""
        SELECT * FROM crls
        WHERE {where_clause}
        ORDER BY {sort_by} {sort_order}
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        results = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]

        crls = [dict(zip(columns, row)) for row in results]

        return crls, total_count

    def exists(self, crl_id: str) -> bool:
        """
        Check if CRL exists.

        Args:
            crl_id: CRL identifier

        Returns:
            bool: True if exists, False otherwise
        """
        result = self.conn.execute(
            "SELECT COUNT(*) FROM crls WHERE id = ?",
            [crl_id]
        ).fetchone()
        return result[0] > 0

    def update(self, crl_id: str, crl_data: Dict[str, Any]) -> bool:
        """
        Update existing CRL.

        Args:
            crl_id: CRL identifier
            crl_data: Updated CRL data

        Returns:
            bool: True if updated, False otherwise
        """
        if not self.exists(crl_id):
            return False

        raw_json = json.dumps(crl_data.get("raw_json", {}))

        query = """
        UPDATE crls SET
            application_number = ?,
            letter_date = ?,
            letter_year = ?,
            letter_type = ?,
            approval_status = ?,
            company_name = ?,
            company_address = ?,
            company_rep = ?,
            approver_name = ?,
            approver_center = ?,
            approver_title = ?,
            file_name = ?,
            text = ?,
            raw_json = ?::JSON,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """

        self.conn.execute(query, [
            crl_data.get("application_number", []),
            crl_data.get("letter_date"),
            crl_data.get("letter_year"),
            crl_data.get("letter_type"),
            crl_data.get("approval_status"),
            crl_data.get("company_name"),
            crl_data.get("company_address"),
            crl_data.get("company_rep"),
            crl_data.get("approver_name"),
            crl_data.get("approver_center", []),
            crl_data.get("approver_title"),
            crl_data.get("file_name"),
            crl_data.get("text"),
            raw_json,
            crl_id,
        ])

        logger.debug(f"Updated CRL: {crl_id}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about CRLs.

        Returns:
            Dict: Statistics including counts by status, year, etc.
        """
        stats = {}

        # Total count
        stats["total_crls"] = self.conn.execute(
            "SELECT COUNT(*) FROM crls"
        ).fetchone()[0]

        # By approval status
        stats["by_status"] = {}
        status_results = self.conn.execute("""
            SELECT approval_status, COUNT(*) as count
            FROM crls
            GROUP BY approval_status
        """).fetchall()
        for status, count in status_results:
            stats["by_status"][status] = count

        # By year
        stats["by_year"] = {}
        year_results = self.conn.execute("""
            SELECT letter_year, COUNT(*) as count
            FROM crls
            GROUP BY letter_year
            ORDER BY letter_year DESC
        """).fetchall()
        for year, count in year_results:
            stats["by_year"][year] = count

        return stats


class SummaryRepository:
    """Repository for CRL summary operations."""

    def __init__(self):
        self.conn = get_db()

    def create(self, summary_data: Dict[str, Any]) -> str:
        """Create a new summary."""
        query = """
        INSERT INTO crl_summaries (id, crl_id, summary, model, tokens_used)
        VALUES (?, ?, ?, ?, ?)
        """
        self.conn.execute(query, [
            summary_data["id"],
            summary_data["crl_id"],
            summary_data["summary"],
            summary_data["model"],
            summary_data.get("tokens_used", 0),
        ])
        return summary_data["id"]

    def get_by_crl_id(self, crl_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a CRL."""
        result = self.conn.execute(
            "SELECT * FROM crl_summaries WHERE crl_id = ?",
            [crl_id]
        ).fetchone()

        if result:
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        return None

    def exists(self, crl_id: str) -> bool:
        """Check if summary exists for CRL."""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM crl_summaries WHERE crl_id = ?",
            [crl_id]
        ).fetchone()
        return result[0] > 0


class EmbeddingRepository:
    """Repository for embedding operations."""

    def __init__(self):
        self.conn = get_db()

    def create(self, embedding_data: Dict[str, Any]) -> str:
        """Create a new embedding."""
        query = """
        INSERT INTO crl_embeddings (id, crl_id, embedding_type, embedding, model)
        VALUES (?, ?, ?, ?, ?)
        """
        self.conn.execute(query, [
            embedding_data["id"],
            embedding_data["crl_id"],
            embedding_data["embedding_type"],
            embedding_data["embedding"],
            embedding_data["model"],
        ])
        return embedding_data["id"]

    def get_by_crl_id(
        self,
        crl_id: str,
        embedding_type: str = "summary"
    ) -> Optional[Dict[str, Any]]:
        """Get embedding for a CRL."""
        result = self.conn.execute(
            "SELECT * FROM crl_embeddings WHERE crl_id = ? AND embedding_type = ?",
            [crl_id, embedding_type]
        ).fetchone()

        if result:
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        return None

    def get_all_embeddings(
        self,
        embedding_type: str = "summary"
    ) -> List[Dict[str, Any]]:
        """Get all embeddings of a specific type."""
        results = self.conn.execute(
            "SELECT * FROM crl_embeddings WHERE embedding_type = ?",
            [embedding_type]
        ).fetchall()

        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in results]

    def exists(self, crl_id: str, embedding_type: str = "summary") -> bool:
        """Check if embedding exists for CRL."""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM crl_embeddings WHERE crl_id = ? AND embedding_type = ?",
            [crl_id, embedding_type]
        ).fetchone()
        return result[0] > 0


class QARepository:
    """Repository for Q&A annotation operations."""

    def __init__(self):
        self.conn = get_db()

    def create(self, qa_data: Dict[str, Any]) -> str:
        """Create a new Q&A record."""
        query = """
        INSERT INTO qa_annotations (id, question, answer, relevant_crl_ids, model, tokens_used)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, [
            qa_data["id"],
            qa_data["question"],
            qa_data["answer"],
            qa_data.get("relevant_crl_ids", []),
            qa_data["model"],
            qa_data.get("tokens_used", 0),
        ])
        return qa_data["id"]

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent Q&A records."""
        results = self.conn.execute(
            """
            SELECT * FROM qa_annotations
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [limit]
        ).fetchall()

        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in results]


class MetadataRepository:
    """Repository for processing metadata operations."""

    def __init__(self):
        self.conn = get_db()

    def set(self, key: str, value: str) -> None:
        """Set or update a metadata value."""
        query = """
        INSERT INTO processing_metadata (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE SET
            value = EXCLUDED.value,
            updated_at = NOW()
        """
        self.conn.execute(query, [key, value])

    def get(self, key: str) -> Optional[str]:
        """Get a metadata value."""
        result = self.conn.execute(
            "SELECT value FROM processing_metadata WHERE key = ?",
            [key]
        ).fetchone()
        return result[0] if result else None
