"""
Search API endpoints for keyword and semantic search.

Provides two search modes:
1. Keyword search - Fast text matching across CRL fields
2. Semantic search - AI-powered embedding-based similarity search
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.database import CRLRepository
from app.models import CRLListItem
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class KeywordSearchRequest(BaseModel):
    """Request for keyword-based search."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(50, ge=1, le=100, description="Number of results per page")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class MatchSnippet(BaseModel):
    """Context snippet around a match."""
    before: str = Field(description="Text before the match")
    match: str = Field(description="The matched text (preserving original case)")
    after: str = Field(description="Text after the match")


class SearchResult(BaseModel):
    """Search result with match context."""
    # CRL basic info
    id: str
    company_name: str
    letter_date: str
    letter_year: str
    application_number: List[str]
    application_type: Optional[str] = None
    therapeutic_category: Optional[str] = None
    deficiency_reason: Optional[str] = None
    summary: Optional[str] = None

    # Match information
    matched_fields: List[str] = Field(description="Fields where matches were found")
    match_snippets: Dict[str, MatchSnippet] = Field(
        description="Context snippets for each matched field"
    )


class KeywordSearchResponse(BaseModel):
    """Response for keyword search."""
    results: List[SearchResult]
    total: int = Field(description="Total number of matching CRLs")
    query: str = Field(description="Original search query")
    limit: int
    offset: int
    has_more: bool = Field(description="Whether there are more results")


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/keyword", response_model=KeywordSearchResponse)
async def keyword_search(request: KeywordSearchRequest):
    """
    Search CRLs using keyword matching across multiple fields.

    Searches across the following fields:
    - company_name
    - product_name
    - therapeutic_category
    - deficiency_reason
    - summary
    - text (full CRL content)

    Returns matching CRLs with highlighted context snippets showing
    where the matches occur.

    **Rate limit**: 60 requests per minute
    """
    try:
        logger.info(f"Keyword search: query='{request.query}', limit={request.limit}, offset={request.offset}")

        # Execute search
        crl_repo = CRLRepository()
        crls_with_context, total = crl_repo.search_keywords(
            query=request.query,
            limit=request.limit,
            offset=request.offset
        )

        # Format results
        results = []
        for crl in crls_with_context:
            # Convert match_snippets to proper MatchSnippet models
            formatted_snippets = {}
            for field, snippet in crl.get('match_snippets', {}).items():
                formatted_snippets[field] = MatchSnippet(**snippet)

            # Convert date to string if it's a date object
            letter_date = crl['letter_date']
            if hasattr(letter_date, 'isoformat'):
                letter_date = letter_date.isoformat()

            result = SearchResult(
                id=crl['id'],
                company_name=crl.get('company_name', ''),
                letter_date=str(letter_date),
                letter_year=crl['letter_year'],
                application_number=crl['application_number'],
                application_type=crl.get('application_type'),
                therapeutic_category=crl.get('therapeutic_category'),
                deficiency_reason=crl.get('deficiency_reason'),
                summary=crl.get('summary'),
                matched_fields=crl.get('matched_fields', []),
                match_snippets=formatted_snippets
            )
            results.append(result)

        # Build response
        response = KeywordSearchResponse(
            results=results,
            total=total,
            query=request.query,
            limit=request.limit,
            offset=request.offset,
            has_more=(request.offset + len(results)) < total
        )

        logger.info(f"Keyword search completed: {len(results)} results (total: {total})")
        return response

    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
