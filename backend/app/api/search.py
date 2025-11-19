"""
Search API endpoints for keyword and semantic search.

Provides two search modes:
1. Keyword search - Fast text matching across CRL fields
2. Semantic search - AI-powered embedding-based similarity search
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import CRLRepository
from app.models import CRLListItem
from app.config import get_settings, Settings
from app.services.rag import RAGService
from app.services.embeddings import EmbeddingsService
from app.utils.logging_config import get_logger
from app.utils.recaptcha import verify_recaptcha, is_recaptcha_enabled

logger = get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


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


class SemanticSearchRequest(BaseModel):
    """Request for semantic (RAG) search."""
    query: str = Field(..., min_length=5, max_length=500, description="Search query for semantic matching")
    top_k: int = Field(5, ge=1, le=20, description="Number of most similar CRLs to return")
    captcha_token: str = Field(..., min_length=1, description="reCAPTCHA v3 token from frontend")


class SemanticResult(BaseModel):
    """Semantic search result with similarity score."""
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

    # Semantic search specific
    similarity_score: float = Field(description="Cosine similarity score (0-1, higher is more similar)")
    relevant_excerpts: List[str] = Field(description="Key excerpts from the CRL text that match the query")


class SemanticSearchResponse(BaseModel):
    """Response for semantic search."""
    results: List[SemanticResult]
    query: str = Field(description="Original search query")
    total_results: int = Field(description="Number of results returned")


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/keyword", response_model=KeywordSearchResponse)
@limiter.limit("60/minute")
async def keyword_search(request: Request, search_request: KeywordSearchRequest):
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
        logger.info(f"Keyword search: query='{search_request.query}', limit={search_request.limit}, offset={search_request.offset}")

        # Execute search
        crl_repo = CRLRepository()
        crls_with_context, total = crl_repo.search_keywords(
            query=search_request.query,
            limit=search_request.limit,
            offset=search_request.offset
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
            query=search_request.query,
            limit=search_request.limit,
            offset=search_request.offset,
            has_more=(search_request.offset + len(results)) < total
        )

        logger.info(f"Keyword search completed: {len(results)} results (total: {total})")
        return response

    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/semantic", response_model=SemanticSearchResponse)
@limiter.limit("10/minute")
async def semantic_search(
    request: Request,
    search_request: SemanticSearchRequest,
    settings: Settings = Depends(get_settings)
):
    """
    Search CRLs using semantic similarity (RAG-based search).

    This endpoint uses AI embeddings to find CRLs that are semantically
    similar to the query, even if they don't contain the exact keywords.

    **Rate limit**: 10 requests per minute (more expensive due to AI processing)
    **Security**: Requires reCAPTCHA v3 token validation

    Args:
        request: Search request with query, top_k, and captcha_token
        settings: Application settings (auto-injected)

    Returns:
        SemanticSearchResponse with similar CRLs and similarity scores
    """
    try:
        logger.info(f"Semantic search: query='{search_request.query}', top_k={search_request.top_k}")

        # 1. Verify reCAPTCHA token
        if is_recaptcha_enabled(settings):
            remote_ip = get_remote_address(request)
            is_valid, score, error_msg = await verify_recaptcha(
                search_request.captcha_token,
                remote_ip,
                settings
            )

            if not is_valid:
                logger.warning(
                    f"reCAPTCHA validation failed for {remote_ip}: {error_msg} (score: {score})"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"reCAPTCHA validation failed: {error_msg}"
                )

            logger.info(f"reCAPTCHA validation passed: score={score:.2f}")

        # 2. Perform semantic search using RAG service
        rag_service = RAGService(settings)

        # Use the RAG service's retrieve method to get similar CRLs
        # (we only need retrieval, not answer generation)
        embeddings_service = EmbeddingsService(settings)

        # Generate query embedding
        query_embedding = embeddings_service.generate_query_embedding(search_request.query)

        # Retrieve similar CRLs
        relevant_crls = rag_service._retrieve_similar_crls(query_embedding, search_request.top_k)

        # 3. Format results
        results = []
        for crl_id, similarity_score, crl_data in relevant_crls:
            # Convert date to string if needed
            letter_date = crl_data['letter_date']
            if hasattr(letter_date, 'isoformat'):
                letter_date = letter_date.isoformat()

            # Extract relevant excerpts from text
            text = crl_data.get('text', '')
            relevant_excerpts = _extract_relevant_excerpts(text, search_request.query, max_excerpts=3)

            result = SemanticResult(
                id=crl_data['id'],
                company_name=crl_data.get('company_name', ''),
                letter_date=str(letter_date),
                letter_year=crl_data['letter_year'],
                application_number=crl_data['application_number'],
                application_type=crl_data.get('application_type'),
                therapeutic_category=crl_data.get('therapeutic_category'),
                deficiency_reason=crl_data.get('deficiency_reason'),
                summary=crl_data.get('summary'),
                similarity_score=round((similarity_score + 1) / 2, 3),  # Normalize cosine to 0-1
                relevant_excerpts=relevant_excerpts
            )
            results.append(result)

        # Build response
        response = SemanticSearchResponse(
            results=results,
            query=search_request.query,
            total_results=len(results)
        )

        logger.info(f"Semantic search completed: {len(results)} results")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions (like reCAPTCHA failures)
        raise

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )


def _extract_relevant_excerpts(text: str, query: str, max_excerpts: int = 3) -> List[str]:
    """
    Extract relevant excerpts from CRL text.

    Args:
        text: Full CRL text
        query: Search query
        max_excerpts: Maximum number of excerpts to return

    Returns:
        List of relevant text excerpts (up to 200 chars each)
    """
    if not text or len(text) < 100:
        return []

    # Split into sentences (simple approach)
    sentences = text.replace('.\n', '.').split('. ')

    # Score sentences by keyword overlap (simple heuristic)
    query_words = set(query.lower().split())
    scored_sentences = []

    for sentence in sentences:
        if len(sentence) < 20:  # Skip very short sentences
            continue

        sentence_words = set(sentence.lower().split())
        overlap = len(query_words & sentence_words)

        if overlap > 0:
            scored_sentences.append((overlap, sentence.strip()))

    # Sort by score and take top excerpts
    scored_sentences.sort(reverse=True, key=lambda x: x[0])
    excerpts = []

    for _, sentence in scored_sentences[:max_excerpts]:
        # Truncate if too long
        excerpt = sentence[:200] + '...' if len(sentence) > 200 else sentence
        excerpts.append(excerpt)

    return excerpts
