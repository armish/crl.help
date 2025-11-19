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

from app.config import get_settings
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
            # Get settings
            settings = get_settings()

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
            """SELECT
                *,
                regexp_extract(application_number[1], '^([A-Z]+)', 1) as application_type
            FROM crls WHERE id = ?""",
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
        approval_status: Optional[List[str]] = None,
        letter_year: Optional[List[str]] = None,
        application_type: Optional[List[str]] = None,
        letter_type: Optional[List[str]] = None,
        therapeutic_category: Optional[List[str]] = None,
        deficiency_reason: Optional[List[str]] = None,
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
            approval_status: Filter by approval status (supports multiple values)
            letter_year: Filter by year (supports multiple values)
            application_type: Filter by application type (supports multiple values)
            letter_type: Filter by letter type (supports multiple values)
            therapeutic_category: Filter by therapeutic category (supports multiple values)
            deficiency_reason: Filter by deficiency reason (supports multiple values)
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

        if approval_status and len(approval_status) > 0:
            placeholders = ','.join(['?' for _ in approval_status])
            where_clauses.append(f"approval_status IN ({placeholders})")
            params.extend(approval_status)

        if letter_year and len(letter_year) > 0:
            placeholders = ','.join(['?' for _ in letter_year])
            where_clauses.append(f"letter_year IN ({placeholders})")
            params.extend(letter_year)

        if application_type and len(application_type) > 0:
            placeholders = ','.join(['?' for _ in application_type])
            where_clauses.append(f"regexp_extract(application_number[1], '^([A-Z]+)', 1) IN ({placeholders})")
            params.extend(application_type)

        if letter_type and len(letter_type) > 0:
            placeholders = ','.join(['?' for _ in letter_type])
            where_clauses.append(f"letter_type IN ({placeholders})")
            params.extend(letter_type)

        if therapeutic_category and len(therapeutic_category) > 0:
            placeholders = ','.join(['?' for _ in therapeutic_category])
            where_clauses.append(f"therapeutic_category IN ({placeholders})")
            params.extend(therapeutic_category)

        if deficiency_reason and len(deficiency_reason) > 0:
            placeholders = ','.join(['?' for _ in deficiency_reason])
            where_clauses.append(f"deficiency_reason IN ({placeholders})")
            params.extend(deficiency_reason)

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
        SELECT
            *,
            regexp_extract(application_number[1], '^([A-Z]+)', 1) as application_type
        FROM crls
        WHERE {where_clause}
        ORDER BY {sort_by} {sort_order}
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        results = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]

        crls = [dict(zip(columns, row)) for row in results]

        return crls, total_count

    def search_keywords(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search CRLs using keyword matching across multiple fields.

        Searches across: company_name, product_name, therapeutic_category,
        deficiency_reason, summary, and text fields.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Tuple[List[Dict], int]: (List of CRLs with match context, total count)

        Each result dict includes:
            - All CRL fields
            - matched_fields: List of field names where matches were found
            - match_snippets: Dict mapping field names to context snippets
        """
        if not query or not query.strip():
            return [], 0

        # Normalize query
        query_lower = query.strip().lower()

        # Fields to search (excluding summary since it's in a separate table)
        search_fields = [
            'c.company_name',
            'c.product_name',
            'c.therapeutic_category',
            'c.deficiency_reason',
            's.summary',
            'c.text'
        ]

        # Build WHERE clause for matching
        conditions = []
        for field in search_fields:
            conditions.append(f"LOWER({field}) LIKE ?")

        where_clause = " OR ".join(conditions)

        # Prepare parameters (same query for each field)
        search_params = [f"%{query_lower}%"] * len(search_fields)

        # Get total count
        count_query = f"""
        SELECT COUNT(DISTINCT c.id)
        FROM crls c
        LEFT JOIN crl_summaries s ON c.id = s.crl_id
        WHERE {where_clause}
        """
        total_count = self.conn.execute(count_query, search_params).fetchone()[0]

        # Get paginated results
        query_sql = f"""
        SELECT
            c.*,
            s.summary,
            regexp_extract(c.application_number[1], '^([A-Z]+)', 1) as application_type
        FROM crls c
        LEFT JOIN crl_summaries s ON c.id = s.crl_id
        WHERE {where_clause}
        ORDER BY c.letter_date DESC
        LIMIT ? OFFSET ?
        """
        params = search_params + [limit, offset]

        results = self.conn.execute(query_sql, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]

        crls_with_context = []
        for row in results:
            crl = dict(zip(columns, row))

            # Extract match information
            matched_fields = []
            match_snippets = {}

            # Map table-qualified field names to actual field names in result
            field_map = {
                'c.company_name': 'company_name',
                'c.product_name': 'product_name',
                'c.therapeutic_category': 'therapeutic_category',
                'c.deficiency_reason': 'deficiency_reason',
                's.summary': 'summary',
                'c.text': 'text'
            }

            for qualified_field, actual_field in field_map.items():
                field_value = crl.get(actual_field)
                if field_value and isinstance(field_value, str):
                    field_value_lower = field_value.lower()
                    if query_lower in field_value_lower:
                        matched_fields.append(actual_field)

                        # Extract context snippet
                        snippet = self._extract_snippet(
                            field_value,
                            query_lower,
                            context_chars=100
                        )
                        match_snippets[actual_field] = snippet

            crl['matched_fields'] = matched_fields
            crl['match_snippets'] = match_snippets
            crls_with_context.append(crl)

        return crls_with_context, total_count

    def _extract_snippet(
        self,
        text: str,
        query: str,
        context_chars: int = 100
    ) -> Dict[str, str]:
        """
        Extract a snippet of text around the query match.

        Args:
            text: Full text to search within
            query: Query string to find
            context_chars: Number of characters to include before/after match

        Returns:
            Dict with 'before', 'match', 'after' keys
        """
        text_lower = text.lower()
        query_lower = query.lower()

        # Find first occurrence
        match_pos = text_lower.find(query_lower)
        if match_pos == -1:
            return {
                'before': '',
                'match': '',
                'after': ''
            }

        # Extract the actual match (preserving original case)
        match_text = text[match_pos:match_pos + len(query)]

        # Extract context before
        start_pos = max(0, match_pos - context_chars)
        before = text[start_pos:match_pos]
        if start_pos > 0:
            # Add ellipsis if truncated
            before = '...' + before.lstrip()

        # Extract context after
        end_pos = min(len(text), match_pos + len(query) + context_chars)
        after = text[match_pos + len(query):end_pos]
        if end_pos < len(text):
            # Add ellipsis if truncated
            after = after.rstrip() + '...'

        return {
            'before': before,
            'match': match_text,
            'after': after
        }

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

        Note:
            Due to a DuckDB limitation with updating array columns,
            this method uses DELETE + INSERT pattern instead of UPDATE.
        """
        if not self.exists(crl_id):
            return False

        # Delete existing record
        self.conn.execute("DELETE FROM crls WHERE id = ?", [crl_id])

        # Insert updated record
        # Ensure id is set correctly
        crl_data["id"] = crl_id
        self.create(crl_data)

        logger.debug(f"Updated CRL: {crl_id}")
        return True

    def get_stats(
        self,
        approval_status: Optional[List[str]] = None,
        letter_year: Optional[List[str]] = None,
        letter_type: Optional[List[str]] = None,
        therapeutic_category: Optional[List[str]] = None,
        deficiency_reason: Optional[List[str]] = None,
        company_name: Optional[List[str]] = None,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about CRLs with optional filters.

        Args:
            approval_status: Filter by approval status (can be a list)
            letter_year: Filter by year (can be a list)
            letter_type: Filter by letter type (can be a list)
            therapeutic_category: Filter by therapeutic category (can be a list)
            deficiency_reason: Filter by deficiency reason (can be a list)
            company_name: Filter by company name (can be a list)
            search_text: Full-text search in text field

        Returns:
            Dict: Statistics including counts by status, year, etc.
        """
        stats = {}

        # Build WHERE clause
        where_clauses = []
        params = []

        if approval_status and len(approval_status) > 0:
            placeholders = ','.join(['?' for _ in approval_status])
            where_clauses.append(f"approval_status IN ({placeholders})")
            params.extend(approval_status)

        if letter_year and len(letter_year) > 0:
            placeholders = ','.join(['?' for _ in letter_year])
            where_clauses.append(f"letter_year IN ({placeholders})")
            params.extend(letter_year)

        if letter_type and len(letter_type) > 0:
            placeholders = ','.join(['?' for _ in letter_type])
            where_clauses.append(f"letter_type IN ({placeholders})")
            params.extend(letter_type)

        if therapeutic_category and len(therapeutic_category) > 0:
            placeholders = ','.join(['?' for _ in therapeutic_category])
            where_clauses.append(f"therapeutic_category IN ({placeholders})")
            params.extend(therapeutic_category)

        if deficiency_reason and len(deficiency_reason) > 0:
            placeholders = ','.join(['?' for _ in deficiency_reason])
            where_clauses.append(f"deficiency_reason IN ({placeholders})")
            params.extend(deficiency_reason)

        if company_name and len(company_name) > 0:
            placeholders = ','.join(['?' for _ in company_name])
            where_clauses.append(f"company_name IN ({placeholders})")
            params.extend(company_name)

        if search_text:
            where_clauses.append("text ILIKE ?")
            params.append(f"%{search_text}%")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Total count
        stats["total_crls"] = self.conn.execute(
            f"SELECT COUNT(*) FROM crls WHERE {where_clause}",
            params
        ).fetchone()[0]

        # By approval status
        stats["by_status"] = {}
        status_results = self.conn.execute(f"""
            SELECT approval_status, COUNT(*) as count
            FROM crls
            WHERE {where_clause}
            GROUP BY approval_status
        """, params).fetchall()
        for status, count in status_results:
            stats["by_status"][status] = count

        # By year
        stats["by_year"] = {}
        year_results = self.conn.execute(f"""
            SELECT letter_year, COUNT(*) as count
            FROM crls
            WHERE {where_clause}
            GROUP BY letter_year
            ORDER BY letter_year DESC
        """, params).fetchall()
        for year, count in year_results:
            stats["by_year"][year] = count

        # By year and status (for stacked bar chart)
        stats["by_year_and_status"] = {}
        year_status_results = self.conn.execute(f"""
            SELECT letter_year, approval_status, COUNT(*) as count
            FROM crls
            WHERE {where_clause}
            GROUP BY letter_year, approval_status
            ORDER BY letter_year DESC, approval_status
        """, params).fetchall()
        for year, status, count in year_status_results:
            if year not in stats["by_year_and_status"]:
                stats["by_year_and_status"][year] = {}
            stats["by_year_and_status"][year][status] = count

        # By application type (extracted from application_number)
        stats["by_application_type"] = {}
        application_type_results = self.conn.execute(f"""
            SELECT
                regexp_extract(application_number[1], '^([A-Z]+)', 1) as application_type,
                COUNT(*) as count
            FROM crls
            WHERE {where_clause}
            AND application_number IS NOT NULL
            AND len(application_number) > 0
            AND regexp_extract(application_number[1], '^([A-Z]+)', 1) IS NOT NULL
            GROUP BY application_type
            ORDER BY count DESC
        """, params).fetchall()
        for app_type, count in application_type_results:
            stats["by_application_type"][app_type] = count

        # By letter type
        stats["by_letter_type"] = {}
        letter_type_results = self.conn.execute(f"""
            SELECT letter_type, COUNT(*) as count
            FROM crls
            WHERE {where_clause} AND letter_type IS NOT NULL AND letter_type != ''
            GROUP BY letter_type
            ORDER BY count DESC
        """, params).fetchall()
        for letter_type, count in letter_type_results:
            stats["by_letter_type"][letter_type] = count

        # By therapeutic category
        stats["by_therapeutic_category"] = {}
        therapeutic_category_results = self.conn.execute(f"""
            SELECT therapeutic_category, COUNT(*) as count
            FROM crls
            WHERE {where_clause} AND therapeutic_category IS NOT NULL AND therapeutic_category != ''
            GROUP BY therapeutic_category
            ORDER BY count DESC
        """, params).fetchall()
        for category, count in therapeutic_category_results:
            stats["by_therapeutic_category"][category] = count

        # By deficiency reason
        stats["by_deficiency_reason"] = {}
        deficiency_reason_results = self.conn.execute(f"""
            SELECT deficiency_reason, COUNT(*) as count
            FROM crls
            WHERE {where_clause} AND deficiency_reason IS NOT NULL AND deficiency_reason != ''
            GROUP BY deficiency_reason
            ORDER BY count DESC
        """, params).fetchall()
        for reason, count in deficiency_reason_results:
            stats["by_deficiency_reason"][reason] = count

        # By year and application type (for stacked bar chart)
        stats["by_year_and_application_type"] = {}
        year_application_type_results = self.conn.execute(f"""
            SELECT
                letter_year,
                regexp_extract(application_number[1], '^([A-Z]+)', 1) as application_type,
                COUNT(*) as count
            FROM crls
            WHERE {where_clause}
            AND application_number IS NOT NULL
            AND len(application_number) > 0
            AND regexp_extract(application_number[1], '^([A-Z]+)', 1) IS NOT NULL
            GROUP BY letter_year, application_type
            ORDER BY letter_year DESC, application_type
        """, params).fetchall()
        for year, app_type, count in year_application_type_results:
            if year not in stats["by_year_and_application_type"]:
                stats["by_year_and_application_type"][year] = {}
            stats["by_year_and_application_type"][year][app_type] = count

        # By year and letter type (for stacked bar chart)
        stats["by_year_and_letter_type"] = {}
        year_letter_type_results = self.conn.execute(f"""
            SELECT letter_year, letter_type, COUNT(*) as count
            FROM crls
            WHERE {where_clause} AND letter_type IS NOT NULL AND letter_type != ''
            GROUP BY letter_year, letter_type
            ORDER BY letter_year DESC, letter_type
        """, params).fetchall()
        for year, letter_type, count in year_letter_type_results:
            if year not in stats["by_year_and_letter_type"]:
                stats["by_year_and_letter_type"][year] = {}
            stats["by_year_and_letter_type"][year][letter_type] = count

        # By year and therapeutic category (for stacked bar chart)
        stats["by_year_and_therapeutic_category"] = {}
        year_therapeutic_category_results = self.conn.execute(f"""
            SELECT letter_year, therapeutic_category, COUNT(*) as count
            FROM crls
            WHERE {where_clause} AND therapeutic_category IS NOT NULL AND therapeutic_category != ''
            GROUP BY letter_year, therapeutic_category
            ORDER BY letter_year DESC, therapeutic_category
        """, params).fetchall()
        for year, category, count in year_therapeutic_category_results:
            if year not in stats["by_year_and_therapeutic_category"]:
                stats["by_year_and_therapeutic_category"][year] = {}
            stats["by_year_and_therapeutic_category"][year][category] = count

        # By year and deficiency reason (for stacked bar chart)
        stats["by_year_and_deficiency_reason"] = {}
        year_deficiency_reason_results = self.conn.execute(f"""
            SELECT letter_year, deficiency_reason, COUNT(*) as count
            FROM crls
            WHERE {where_clause} AND deficiency_reason IS NOT NULL AND deficiency_reason != ''
            GROUP BY letter_year, deficiency_reason
            ORDER BY letter_year DESC, deficiency_reason
        """, params).fetchall()
        for year, reason, count in year_deficiency_reason_results:
            if year not in stats["by_year_and_deficiency_reason"]:
                stats["by_year_and_deficiency_reason"][year] = {}
            stats["by_year_and_deficiency_reason"][year][reason] = count

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

    def get_summaries_by_crl_ids(self, crl_ids: List[str]) -> List[Dict[str, Any]]:
        """Get summaries for multiple CRLs."""
        if not crl_ids:
            return []

        # Build parameterized query for batch fetch
        placeholders = ",".join(["?" for _ in crl_ids])
        query = f"SELECT * FROM crl_summaries WHERE crl_id IN ({placeholders})"

        results = self.conn.execute(query, crl_ids).fetchall()

        summaries = []
        if results:
            columns = [desc[0] for desc in self.conn.description]
            summaries = [dict(zip(columns, row)) for row in results]

        return summaries


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

    def get_embeddings_for_search(
        self,
        embedding_type: str = "summary"
    ) -> List[Dict[str, Any]]:
        """
        Get embeddings optimized for similarity search.

        Only fetches crl_id and embedding vector (not metadata),
        which is much faster than get_all_embeddings().

        Args:
            embedding_type: Type of embedding to retrieve

        Returns:
            List of dicts with 'crl_id' and 'embedding' keys
        """
        results = self.conn.execute(
            """
            SELECT crl_id, embedding
            FROM crl_embeddings
            WHERE embedding_type = ?
            """,
            [embedding_type]
        ).fetchall()

        return [{"crl_id": row[0], "embedding": row[1]} for row in results]

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
        VALUES (?, ?, NOW())
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
