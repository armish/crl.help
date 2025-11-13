"""
Pydantic models for API request/response validation.

These models define the structure of data exchanged between
the FastAPI backend and frontend clients.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# CRL Models
# ============================================================================

class CRLBase(BaseModel):
    """Base CRL data (common fields)."""
    id: str
    application_number: List[str]
    letter_date: str
    letter_year: str
    approval_status: str
    company_name: str
    approver_center: List[str]


class CRLListItem(CRLBase):
    """CRL item in list view (subset of fields for performance)."""
    pass


class CRLDetail(CRLBase):
    """Detailed CRL view with all fields."""
    letter_type: Optional[str] = None
    company_address: Optional[str] = None
    company_rep: Optional[str] = None
    approver_name: Optional[str] = None
    approver_title: Optional[str] = None
    file_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CRLWithSummary(CRLDetail):
    """CRL with AI-generated summary."""
    summary: Optional[str] = None
    summary_model: Optional[str] = None


class CRLWithText(CRLWithSummary):
    """CRL with full text content."""
    text: str


class CRLListResponse(BaseModel):
    """Paginated list of CRLs."""
    items: List[CRLListItem]
    total: int
    limit: int
    offset: int
    has_more: bool = Field(description="Whether there are more results")


# ============================================================================
# Filter and Query Models
# ============================================================================

class CRLFilterParams(BaseModel):
    """Query parameters for filtering CRLs."""
    approval_status: Optional[str] = Field(None, description="Filter by approval status")
    letter_year: Optional[str] = Field(None, description="Filter by year")
    company_name: Optional[str] = Field(None, description="Filter by company name (partial match)")
    search_text: Optional[str] = Field(None, description="Full-text search in letter content")
    sort_by: str = Field("letter_date", description="Field to sort by")
    sort_order: str = Field("DESC", description="Sort direction (ASC or DESC)")
    limit: int = Field(50, ge=1, le=100, description="Number of results per page")
    offset: int = Field(0, ge=0, description="Number of results to skip")


# ============================================================================
# Statistics Models
# ============================================================================

class StatsOverview(BaseModel):
    """Overall statistics about CRLs."""
    total_crls: int
    by_status: dict  # {"Approved": 295, "Unapproved": 97}
    by_year: dict  # {"2024": 67, "2023": 27, ...}


class CompanyStats(BaseModel):
    """Company-level statistics."""
    company_name: str
    crl_count: int
    approved_count: int
    unapproved_count: int


class CompanyStatsResponse(BaseModel):
    """List of top companies by CRL count."""
    companies: List[CompanyStats]
    total_companies: int


# ============================================================================
# Q&A Models
# ============================================================================

class QARequest(BaseModel):
    """Request to ask a question."""
    question: str = Field(..., min_length=5, max_length=500, description="Question to ask")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of relevant CRLs to retrieve")


class QAResponse(BaseModel):
    """Response to a Q&A query."""
    question: str
    answer: str
    relevant_crls: List[str] = Field(description="IDs of CRLs used to answer")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")
    model: str = Field(description="AI model used")


class QAHistoryItem(BaseModel):
    """Historical Q&A item."""
    id: str
    question: str
    answer: str
    relevant_crl_ids: List[str]
    model: str
    created_at: datetime


class QAHistoryResponse(BaseModel):
    """List of historical Q&A interactions."""
    items: List[QAHistoryItem]
    total: int


# ============================================================================
# Export Models
# ============================================================================

class ExportRequest(BaseModel):
    """Request to export CRL data."""
    format: str = Field("csv", description="Export format: 'csv' or 'excel'")
    include_summaries: bool = Field(True, description="Include AI summaries")
    filters: Optional[CRLFilterParams] = Field(None, description="Apply filters to export")


# ============================================================================
# Health Check Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("healthy", description="Service status")
    database: str = Field(description="Database connection status")
    total_crls: int = Field(description="Number of CRLs in database")
    total_summaries: int = Field(description="Number of summaries generated")
    total_embeddings: int = Field(description="Number of embeddings generated")
