"""
Sitemap API endpoint.

Provides XML sitemap for search engine crawlers to discover all pages.
"""

from fastapi import APIRouter, Response
from fastapi.responses import Response as FastAPIResponse
from app.database import CRLRepository
from app.utils.sitemap import generate_sitemap_xml
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize repository
crl_repo = CRLRepository()


@router.get("/sitemap.xml", response_class=FastAPIResponse)
async def get_sitemap():
    """
    Generate and return XML sitemap for all pages.

    Returns XML sitemap containing:
    - Static pages (homepage, about, CRL index)
    - All CRL detail pages with SEO-friendly URLs

    Example:
        GET /sitemap.xml

    Returns:
        XML sitemap with all URLs
    """
    try:
        # Fetch all CRLs (we need all of them for the sitemap)
        # get_all returns (items, total) tuple
        crls, total = crl_repo.get_all(
            limit=10000,  # High limit to get all CRLs
            offset=0,
            sort_by="letter_date",
            sort_order="DESC"
        )

        logger.info(f"Generating sitemap with {len(crls)} CRLs (total: {total})")

        # Generate sitemap XML
        sitemap_xml = generate_sitemap_xml(crls, base_url="https://crl.help")

        # Return XML response with proper content type
        return Response(
            content=sitemap_xml,
            media_type="application/xml",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            }
        )

    except Exception as e:
        logger.error(f"Error generating sitemap: {e}")
        # Return minimal sitemap on error
        minimal_sitemap = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://crl.help/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>'''
        return Response(
            content=minimal_sitemap,
            media_type="application/xml"
        )
