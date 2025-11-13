"""
CRL API endpoints for listing, filtering, and viewing Complete Response Letters.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.database import CRLRepository, SummaryRepository
from app.models import (
    CRLListResponse,
    CRLListItem,
    CRLWithSummary,
    CRLWithText
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Initialize repositories
crl_repo = CRLRepository()
summary_repo = SummaryRepository()


@router.get("", response_model=CRLListResponse)
async def list_crls(
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    letter_year: Optional[str] = Query(None, description="Filter by year"),
    letter_type: Optional[str] = Query(None, description="Filter by letter type (BLA, NDA, etc.)"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    search_text: Optional[str] = Query(None, description="Full-text search in letter content"),
    sort_by: str = Query("letter_date", description="Field to sort by"),
    sort_order: str = Query("DESC", description="Sort direction (ASC or DESC)"),
    limit: int = Query(50, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List CRLs with filtering, sorting, and pagination.

    Returns a paginated list of CRLs matching the specified criteria.

    ## Filters

    - **approval_status**: "Approved" or "Unapproved"
    - **letter_year**: Year as string (e.g., "2024")
    - **company_name**: Partial company name (case-insensitive)
    - **search_text**: Full-text search in letter content

    ## Sorting

    - **sort_by**: Column to sort by (default: letter_date)
    - **sort_order**: ASC or DESC (default: DESC)

    ## Pagination

    - **limit**: Results per page (1-100, default: 50)
    - **offset**: Number of results to skip (default: 0)
    """
    try:
        crls, total_count = crl_repo.get_all(
            limit=limit,
            offset=offset,
            approval_status=approval_status,
            letter_year=letter_year,
            letter_type=letter_type,
            company_name=company_name,
            search_text=search_text,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Convert to response model
        items = [
            CRLListItem(
                id=crl["id"],
                application_number=crl["application_number"] or [],
                letter_date=str(crl["letter_date"]) if crl["letter_date"] else "",
                letter_year=crl["letter_year"] or "",
                letter_type=crl["letter_type"],
                approval_status=crl["approval_status"] or "",
                company_name=crl["company_name"] or "",
                approver_center=crl["approver_center"] or []
            )
            for crl in crls
        ]

        has_more = (offset + limit) < total_count

        return CRLListResponse(
            items=items,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=has_more
        )

    except Exception as e:
        logger.error(f"Error listing CRLs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve CRLs")


@router.get("/detail", response_model=CRLWithSummary)
async def get_crl(crl_id: str = Query(..., description="CRL ID")):
    """
    Get detailed information about a specific CRL including AI summary.

    Returns full CRL metadata with AI-generated summary if available.

    ## Response includes:

    - All CRL metadata (application number, company, dates, etc.)
    - AI-generated summary (if available)
    - Summary model information

    Note: Use `GET /crls/text?crl_id=...` to also retrieve full letter text.
    """
    try:
        # Get CRL data
        crl = crl_repo.get_by_id(crl_id)

        if not crl:
            raise HTTPException(status_code=404, detail=f"CRL not found: {crl_id}")

        # Get summary if available
        summary_data = summary_repo.get_by_crl_id(crl_id)

        return CRLWithSummary(
            id=crl["id"],
            application_number=crl["application_number"] or [],
            letter_date=str(crl["letter_date"]) if crl["letter_date"] else "",
            letter_year=crl["letter_year"] or "",
            approval_status=crl["approval_status"] or "",
            company_name=crl["company_name"] or "",
            approver_center=crl["approver_center"] or [],
            letter_type=crl.get("letter_type"),
            company_address=crl.get("company_address"),
            company_rep=crl.get("company_rep"),
            approver_name=crl.get("approver_name"),
            approver_title=crl.get("approver_title"),
            file_name=crl.get("file_name"),
            created_at=crl["created_at"],
            updated_at=crl["updated_at"],
            summary=summary_data["summary"] if summary_data else None,
            summary_model=summary_data["model"] if summary_data else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving CRL {crl_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve CRL")


@router.get("/text", response_model=CRLWithText)
async def get_crl_with_text(crl_id: str = Query(..., description="CRL ID")):
    """
    Get complete CRL information including full letter text.

    Returns all CRL data including the complete letter text content.

    **Warning**: Response may be large (5-50KB) due to full text content.

    ## Response includes:

    - All CRL metadata
    - AI-generated summary (if available)
    - **Full letter text** (complete CRL content)
    """
    try:
        # Get CRL data
        crl = crl_repo.get_by_id(crl_id)

        if not crl:
            raise HTTPException(status_code=404, detail=f"CRL not found: {crl_id}")

        # Get summary if available
        summary_data = summary_repo.get_by_crl_id(crl_id)

        return CRLWithText(
            id=crl["id"],
            application_number=crl["application_number"] or [],
            letter_date=str(crl["letter_date"]) if crl["letter_date"] else "",
            letter_year=crl["letter_year"] or "",
            approval_status=crl["approval_status"] or "",
            company_name=crl["company_name"] or "",
            approver_center=crl["approver_center"] or [],
            letter_type=crl.get("letter_type"),
            company_address=crl.get("company_address"),
            company_rep=crl.get("company_rep"),
            approver_name=crl.get("approver_name"),
            approver_title=crl.get("approver_title"),
            file_name=crl.get("file_name"),
            created_at=crl["created_at"],
            updated_at=crl["updated_at"],
            summary=summary_data["summary"] if summary_data else None,
            summary_model=summary_data["model"] if summary_data else None,
            text=crl.get("text", "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving CRL text for {crl_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve CRL text")
