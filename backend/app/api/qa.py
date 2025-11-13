"""
Q&A API endpoints for RAG-powered question answering over CRL data.
"""

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.database import QARepository
from app.services.rag import RAGService
from app.models import QARequest, QAResponse, QAHistoryResponse, QAHistoryItem
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Initialize services
settings = get_settings()
rag_service = RAGService(settings)
qa_repo = QARepository()


@router.post("/ask", response_model=QAResponse)
async def ask_question(request: QARequest):
    """
    Ask a question and get an AI-powered answer based on relevant CRLs.

    Uses RAG (Retrieval-Augmented Generation) to:
    1. Find the most relevant CRLs using semantic search
    2. Generate an answer based on the retrieved context

    ## How it works

    1. **Query Embedding**: Your question is converted to a vector embedding
    2. **Semantic Search**: Finds CRLs with similar semantic meaning
    3. **Context Building**: Top-k relevant CRLs are used as context
    4. **Answer Generation**: AI generates an answer citing specific CRLs

    ## Parameters

    - **question**: Your question (5-500 characters)
    - **top_k**: Number of relevant CRLs to retrieve (1-20, default: 5)

    ## Example Questions

    - "What are common CMC deficiencies in biologics?"
    - "Which companies received the most CRLs in 2024?"
    - "What are typical clinical trial deficiencies?"
    - "How do manufacturing issues affect CRL outcomes?"

    ## Response

    Returns an answer with:
    - **answer**: AI-generated response
    - **relevant_crls**: IDs of CRLs used for context
    - **confidence**: Confidence score (0-1)
    - **model**: AI model used
    """
    try:
        logger.info(f"Received Q&A request: {request.question[:100]}...")

        # Call RAG service
        result = rag_service.answer_question(
            question=request.question,
            top_k=request.top_k,
            save_to_db=True  # Save to database for history
        )

        return QAResponse(
            question=result["question"],
            answer=result["answer"],
            relevant_crls=result["relevant_crls"],
            confidence=result["confidence"],
            model=result["model"]
        )

    except ValueError as e:
        # Validation errors (e.g., empty question, no embeddings)
        logger.warning(f"Validation error in Q&A: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing Q&A request: {e}")
        raise HTTPException(status_code=500, detail="Failed to process question")


@router.get("/history", response_model=QAHistoryResponse)
async def get_qa_history(limit: int = 10):
    """
    Get recent Q&A history.

    Returns the most recent questions and answers.

    ## Parameters

    - **limit**: Maximum number of Q&A pairs to return (default: 10)

    ## Use Cases

    - Show recent queries on the frontend
    - Provide query suggestions
    - Track popular questions

    ## Response

    Returns a list of recent Q&A interactions with:
    - Question text
    - Answer text
    - Relevant CRL IDs
    - Model used
    - Timestamp
    """
    try:
        qa_records = qa_repo.get_recent(limit=limit)

        items = [
            QAHistoryItem(
                id=record["id"],
                question=record["question"],
                answer=record["answer"],
                relevant_crl_ids=record.get("relevant_crl_ids", []),
                model=record["model"],
                created_at=record["created_at"]
            )
            for record in qa_records
        ]

        return QAHistoryResponse(
            items=items,
            total=len(items)
        )

    except Exception as e:
        logger.error(f"Error fetching Q&A history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve Q&A history")
