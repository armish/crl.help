"""
PDF proxy API endpoints.

Provides endpoints to proxy FDA-hosted PDF files to avoid CORS issues
when displaying PDFs in the frontend with PDF.js.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pdf", tags=["PDF"])


@router.get("/proxy")
async def proxy_pdf(
    url: str = Query(..., description="URL of the PDF to proxy")
):
    """
    Proxy a PDF file from an external URL (typically FDA).

    This endpoint fetches a PDF from an external source and streams it back
    to the client. This is necessary to avoid CORS issues when using PDF.js
    to display PDFs from external domains.

    Args:
        url: Full URL of the PDF file to fetch

    Returns:
        StreamingResponse with PDF content

    Raises:
        HTTPException: If URL is invalid or PDF cannot be fetched
    """
    # Validate that URL is from FDA
    allowed_domains = [
        "fda.gov",
        "www.fda.gov",
        "download.open.fda.gov"
    ]

    if not any(domain in url.lower() for domain in allowed_domains):
        raise HTTPException(
            status_code=400,
            detail="Only FDA URLs are allowed for security reasons"
        )

    try:
        # Fetch the PDF
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            logger.info(f"Proxying PDF from: {url}")
            response = await client.get(url)
            response.raise_for_status()

            # Verify content type is PDF
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and "application/octet-stream" not in content_type:
                logger.warning(f"Unexpected content type: {content_type} for URL: {url}")
                # Still allow it, as some servers don't set proper content-type

            # Stream the PDF back to the client
            return StreamingResponse(
                iter([response.content]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=crl.pdf",
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                }
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching PDF from {url}: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to fetch PDF: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error fetching PDF from {url}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch PDF from source: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error proxying PDF from {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while proxying PDF"
        )
