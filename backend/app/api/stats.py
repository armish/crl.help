"""
Statistics API endpoints for CRL analytics and trends.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.database import CRLRepository
from app.models import StatsOverview, CompanyStats, CompanyStatsResponse
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Initialize repository
crl_repo = CRLRepository()


@router.get("/overview", response_model=StatsOverview)
async def get_stats_overview(
    approval_status: List[str] = Query(None),
    letter_year: List[str] = Query(None),
    company_name: List[str] = Query(None),
    search_text: str = None
):
    """
    Get overall statistics about CRLs in the database with optional filters.

    Returns aggregate statistics including:
    - Total CRL count
    - Breakdown by approval status
    - Breakdown by year

    ## Query Parameters

    - **approval_status**: Filter by approval status (e.g., "Approved", "Unapproved")
    - **letter_year**: Filter by year (e.g., "2024")
    - **company_name**: Filter by company name (partial match)
    - **search_text**: Full-text search in letter text

    ## Example Response

    ```json
    {
      "total_crls": 783,
      "by_status": {
        "Approved": 590,
        "Unapproved": 193
      },
      "by_year": {
        "2025": 40,
        "2024": 67,
        "2023": 27,
        ...
      }
    }
    ```
    """
    try:
        stats = crl_repo.get_stats(
            approval_status=approval_status,
            letter_year=letter_year,
            company_name=company_name,
            search_text=search_text
        )

        return StatsOverview(
            total_crls=stats["total_crls"],
            by_status=stats["by_status"],
            by_year=stats["by_year"]
        )

    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/companies", response_model=CompanyStatsResponse)
async def get_company_stats(limit: int = 20):
    """
    Get statistics grouped by company.

    Returns companies ordered by CRL count (descending).

    ## Parameters

    - **limit**: Maximum number of companies to return (default: 20)

    ## Example Response

    ```json
    {
      "companies": [
        {
          "company_name": "Novartis Pharmaceuticals",
          "crl_count": 15,
          "approved_count": 12,
          "unapproved_count": 3
        },
        ...
      ],
      "total_companies": 245
    }
    ```
    """
    try:
        conn = crl_repo.conn

        # Get company statistics
        query = """
        SELECT
            company_name,
            COUNT(*) as crl_count,
            SUM(CASE WHEN approval_status = 'Approved' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN approval_status = 'Unapproved' THEN 1 ELSE 0 END) as unapproved_count
        FROM crls
        WHERE company_name IS NOT NULL AND company_name != ''
        GROUP BY company_name
        ORDER BY crl_count DESC
        LIMIT ?
        """

        results = conn.execute(query, [limit]).fetchall()

        companies = [
            CompanyStats(
                company_name=row[0],
                crl_count=row[1],
                approved_count=row[2],
                unapproved_count=row[3]
            )
            for row in results
        ]

        # Get total unique companies
        total_companies = conn.execute("""
            SELECT COUNT(DISTINCT company_name)
            FROM crls
            WHERE company_name IS NOT NULL AND company_name != ''
        """).fetchone()[0]

        return CompanyStatsResponse(
            companies=companies,
            total_companies=total_companies
        )

    except Exception as e:
        logger.error(f"Error fetching company statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve company statistics")
