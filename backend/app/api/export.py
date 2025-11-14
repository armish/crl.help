"""
Export API endpoints for downloading CRL data in various formats.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime

from app.database import CRLRepository, SummaryRepository
from app.services.export_service import ExportService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Initialize repositories
crl_repo = CRLRepository()
summary_repo = SummaryRepository()


@router.get("/csv")
async def export_csv(
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    letter_year: Optional[str] = Query(None, description="Filter by year"),
    application_type: Optional[str] = Query(None, description="Filter by application type"),
    letter_type: Optional[str] = Query(None, description="Filter by letter type"),
    therapeutic_category: Optional[str] = Query(None, description="Filter by therapeutic category"),
    deficiency_reason: Optional[str] = Query(None, description="Filter by deficiency reason"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    search_text: Optional[str] = Query(None, description="Full-text search in letter content"),
    include_summary: bool = Query(False, description="Include AI-generated summaries"),
    sort_by: str = Query("letter_date", description="Field to sort by"),
    sort_order: str = Query("DESC", description="Sort direction (ASC or DESC)"),
):
    """
    Export CRLs to CSV format with optional filtering.

    This endpoint returns all matching CRLs (no pagination limit) in CSV format.
    Filters work the same as the /api/crls endpoint.

    ## Parameters

    - **include_summary**: Include AI-generated summary column (default: false)
    - All other filter parameters work the same as /api/crls endpoint

    ## Returns

    CSV file download with appropriate headers
    """
    try:
        logger.info(f"CSV export requested with filters: approval_status={approval_status}, "
                    f"year={letter_year}, include_summary={include_summary}")

        # Get all matching CRLs (no pagination limit for export)
        crls, total_count = crl_repo.get_all(
            limit=None,  # No limit for export
            offset=0,
            approval_status=approval_status,
            letter_year=letter_year,
            application_type=application_type,
            letter_type=letter_type,
            therapeutic_category=therapeutic_category,
            deficiency_reason=deficiency_reason,
            company_name=company_name,
            search_text=search_text,
            sort_by=sort_by,
            sort_order=sort_order
        )

        if not crls:
            raise HTTPException(status_code=404, detail="No CRLs found matching the specified criteria")

        # Convert to dictionaries for export
        crl_dicts = [dict(crl) for crl in crls]

        # Add summaries if requested
        if include_summary:
            crl_ids = [crl["id"] for crl in crl_dicts]
            summaries = summary_repo.get_summaries_by_crl_ids(crl_ids)
            summary_dict = {s["crl_id"]: s["summary"] for s in summaries}

            for crl in crl_dicts:
                crl["summary"] = summary_dict.get(crl["id"])

        # Generate CSV
        csv_output = ExportService.export_to_csv(crl_dicts, include_summary=include_summary)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crl_export_{timestamp}.csv"

        logger.info(f"✓ CSV export successful: {len(crl_dicts)} CRLs, filename={filename}")

        # Return as streaming response
        return StreamingResponse(
            iter([csv_output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export CSV failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/excel")
async def export_excel(
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    letter_year: Optional[str] = Query(None, description="Filter by year"),
    application_type: Optional[str] = Query(None, description="Filter by application type"),
    letter_type: Optional[str] = Query(None, description="Filter by letter type"),
    therapeutic_category: Optional[str] = Query(None, description="Filter by therapeutic category"),
    deficiency_reason: Optional[str] = Query(None, description="Filter by deficiency reason"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    search_text: Optional[str] = Query(None, description="Full-text search in letter content"),
    include_summary: bool = Query(False, description="Include AI-generated summaries"),
    sort_by: str = Query("letter_date", description="Field to sort by"),
    sort_order: str = Query("DESC", description="Sort direction (ASC or DESC)"),
):
    """
    Export CRLs to Excel format with optional filtering.

    This endpoint returns all matching CRLs (no pagination limit) in Excel format.
    Filters work the same as the /api/crls endpoint.

    ## Parameters

    - **include_summary**: Include AI-generated summary column (default: false)
    - All other filter parameters work the same as /api/crls endpoint

    ## Returns

    Excel (.xlsx) file download with appropriate headers
    """
    try:
        logger.info(f"Excel export requested with filters: approval_status={approval_status}, "
                    f"year={letter_year}, include_summary={include_summary}")

        # Get all matching CRLs (no pagination limit for export)
        crls, total_count = crl_repo.get_all(
            limit=None,  # No limit for export
            offset=0,
            approval_status=approval_status,
            letter_year=letter_year,
            application_type=application_type,
            letter_type=letter_type,
            therapeutic_category=therapeutic_category,
            deficiency_reason=deficiency_reason,
            company_name=company_name,
            search_text=search_text,
            sort_by=sort_by,
            sort_order=sort_order
        )

        if not crls:
            raise HTTPException(status_code=404, detail="No CRLs found matching the specified criteria")

        # Convert to dictionaries for export
        crl_dicts = [dict(crl) for crl in crls]

        # Add summaries if requested
        if include_summary:
            crl_ids = [crl["id"] for crl in crl_dicts]
            summaries = summary_repo.get_summaries_by_crl_ids(crl_ids)
            summary_dict = {s["crl_id"]: s["summary"] for s in summaries}

            for crl in crl_dicts:
                crl["summary"] = summary_dict.get(crl["id"])

        # Generate Excel
        excel_output = ExportService.export_to_excel(crl_dicts, include_summary=include_summary)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crl_export_{timestamp}.xlsx"

        logger.info(f"✓ Excel export successful: {len(crl_dicts)} CRLs, filename={filename}")

        # Return as streaming response
        return StreamingResponse(
            iter([excel_output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError as e:
        logger.error(f"Excel export failed - openpyxl not installed: {e}")
        raise HTTPException(
            status_code=501,
            detail="Excel export requires openpyxl. Please install it with: pip install openpyxl"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export Excel failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
