"""
RAG (Retrieval-Augmented Generation) service for CRL Q&A.

This module implements a RAG system that:
1. Takes a user question
2. Retrieves the most relevant CRLs using semantic similarity
3. Generates an answer based on the retrieved context
"""

import logging
from typing import List, Dict, Any, Optional
from app.config import Settings
from app.database import CRLRepository, EmbeddingRepository, QARepository
from app.services.embeddings import EmbeddingsService
from app.utils.openai_client import OpenAIClient
from app.utils.vector_utils import find_top_k_similar

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for question answering over CRL data.

    Combines semantic retrieval (finding relevant CRLs) with
    language generation (answering questions) using OpenAI.

    Attributes:
        settings: Application settings
        openai_client: OpenAI client wrapper
        embeddings_service: Service for generating embeddings
        crl_repo: Repository for CRL operations
        embedding_repo: Repository for embedding operations
        qa_repo: Repository for Q&A operations
    """

    def __init__(self, settings: Settings):
        """
        Initialize RAG service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.openai_client = OpenAIClient(settings)
        self.embeddings_service = EmbeddingsService(settings)
        self.crl_repo = CRLRepository()
        self.embedding_repo = EmbeddingRepository()
        self.qa_repo = QARepository()

    def answer_question(
        self,
        question: str,
        top_k: Optional[int] = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG over CRL data.

        Args:
            question: User's question
            top_k: Number of relevant CRLs to retrieve (default: from settings)
            save_to_db: Whether to save Q&A to database

        Returns:
            Dict containing:
                - question: The original question
                - answer: Generated answer
                - relevant_crls: List of relevant CRL IDs used
                - confidence: Confidence score (0-1)
                - model: Model used for generation

        Raises:
            ValueError: If question is empty or no CRLs found
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        if top_k is None:
            top_k = self.settings.rag_top_k

        logger.info(f"Answering question (top_k={top_k}): {question[:100]}...")

        # Step 1: Generate query embedding
        try:
            query_embedding = self.embeddings_service.generate_query_embedding(question)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

        # Step 2: Retrieve top-k most similar CRLs
        try:
            relevant_crls = self._retrieve_similar_crls(query_embedding, top_k)
        except Exception as e:
            logger.error(f"Failed to retrieve similar CRLs: {e}")
            raise

        if not relevant_crls:
            return {
                "question": question,
                "answer": "I couldn't find any relevant CRLs to answer this question. "
                         "Please try rephrasing or ask about a different topic.",
                "relevant_crls": [],
                "confidence": 0.0,
                "model": self.settings.openai_qa_model
            }

        # Step 3: Generate answer using retrieved context
        try:
            answer, crl_ids = self._generate_answer(question, relevant_crls)
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise

        # Step 4: Compute confidence score based on similarity scores
        confidence = self._compute_confidence(relevant_crls)

        result = {
            "question": question,
            "answer": answer,
            "relevant_crls": crl_ids,
            "confidence": confidence,
            "model": self.settings.openai_qa_model
        }

        # Step 5: Save to database if requested
        if save_to_db and not self.settings.ai_dry_run:
            try:
                self._save_qa(result)
            except Exception as e:
                logger.warning(f"Failed to save Q&A to database: {e}")

        logger.info(f"Generated answer with {len(crl_ids)} relevant CRLs")
        return result

    def _retrieve_similar_crls(
        self,
        query_embedding: List[float],
        top_k: int
    ) -> List[tuple[str, float, Dict[str, Any]]]:
        """
        Retrieve top-k most similar CRLs based on query embedding.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to retrieve

        Returns:
            List of (crl_id, similarity_score, crl_data) tuples

        Raises:
            ValueError: If no embeddings found in database
        """
        # Get all embeddings from database
        all_embeddings = self.embedding_repo.get_all_embeddings(
            embedding_type="summary"
        )

        if not all_embeddings:
            raise ValueError("No CRL embeddings found in database")

        # Prepare candidate vectors
        candidates = []
        for emb_record in all_embeddings:
            crl_id = emb_record["crl_id"]
            embedding = emb_record["embedding"]
            candidates.append((crl_id, embedding))

        # Find top-k similar
        top_results = find_top_k_similar(
            query_vec=query_embedding,
            candidate_vecs=candidates,
            k=top_k,
            similarity_fn="cosine"
        )

        # Fetch full CRL data for top results
        results = []
        for crl_id, similarity_score in top_results:
            crl_data = self.crl_repo.get_by_id(crl_id)
            if crl_data:
                results.append((crl_id, similarity_score, crl_data))
                logger.debug(
                    f"Retrieved CRL {crl_id} with similarity {similarity_score:.3f}"
                )

        return results

    def _generate_answer(
        self,
        question: str,
        relevant_crls: List[tuple[str, float, Dict[str, Any]]]
    ) -> tuple[str, List[str]]:
        """
        Generate answer using relevant CRLs as context.

        Args:
            question: User's question
            relevant_crls: List of (crl_id, score, crl_data) tuples

        Returns:
            Tuple of (answer, list of crl_ids used)
        """
        # Build context from relevant CRLs
        context_parts = []
        crl_ids = []

        for crl_id, score, crl_data in relevant_crls:
            crl_ids.append(crl_id)

            # Extract key information
            app_num = crl_data.get("application_number", ["N/A"])[0] if crl_data.get("application_number") else "N/A"
            company = crl_data.get("company_name", "N/A")
            date = crl_data.get("letter_date", "N/A")
            text = crl_data.get("text", "")

            # Truncate very long texts
            if len(text) > 3000:
                text = text[:3000] + "...[truncated]"

            context_parts.append(
                f"[CRL #{len(context_parts) + 1}]\n"
                f"Application: {app_num}\n"
                f"Company: {company}\n"
                f"Date: {date}\n"
                f"Content: {text}\n"
            )

        context = "\n\n".join(context_parts)

        # Create prompt
        prompt = self._create_qa_prompt(question, context)

        # Generate answer
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert assistant specializing in FDA Complete Response Letters. "
                    "Answer questions accurately based on the provided CRL context. "
                    "If the context doesn't contain enough information, say so clearly. "
                    "Always cite which CRL(s) you're referencing in your answer."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        answer = self.openai_client.create_chat_completion(
            model=self.settings.openai_qa_model,
            messages=messages,
            temperature=0.5,  # Moderate temperature for balanced creativity/accuracy
            max_tokens=800
        )

        return answer.strip(), crl_ids

    def _create_qa_prompt(self, question: str, context: str) -> str:
        """
        Create the prompt for Q&A generation.

        Args:
            question: User's question
            context: Context from retrieved CRLs

        Returns:
            Formatted prompt
        """
        prompt = f"""Based on the following Complete Response Letters (CRLs), please answer this question:

Question: {question}

Context from relevant CRLs:
{context}

Please provide a clear and accurate answer based on the CRL context above. If the CRLs don't contain enough information to answer the question fully, acknowledge this limitation. Reference specific CRLs (by number) when making claims."""

        return prompt

    def _compute_confidence(
        self,
        relevant_crls: List[tuple[str, float, Dict[str, Any]]]
    ) -> float:
        """
        Compute confidence score based on similarity scores.

        Args:
            relevant_crls: List of (crl_id, score, crl_data) tuples

        Returns:
            Confidence score between 0 and 1
        """
        if not relevant_crls:
            return 0.0

        # Use the top similarity score as confidence
        # Cosine similarity ranges from -1 to 1, normalize to 0-1
        top_score = relevant_crls[0][1]
        confidence = (top_score + 1) / 2

        # Boost confidence if multiple CRLs have high similarity
        if len(relevant_crls) >= 3:
            avg_top3 = sum(score for _, score, _ in relevant_crls[:3]) / 3
            avg_top3_normalized = (avg_top3 + 1) / 2
            confidence = (confidence + avg_top3_normalized) / 2

        return round(confidence, 3)

    def _save_qa(self, qa_data: Dict[str, Any]) -> None:
        """
        Save Q&A result to database.

        Args:
            qa_data: Q&A data to save
        """
        import uuid

        qa_record = {
            "id": str(uuid.uuid4()),
            "question": qa_data["question"],
            "answer": qa_data["answer"],
            "relevant_crl_ids": qa_data["relevant_crls"],
            "model": qa_data["model"],
            "tokens_used": 0  # Could be tracked if needed
        }

        self.qa_repo.create(qa_record)
        logger.info(f"Saved Q&A to database: {qa_record['id']}")

    def get_recent_questions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent questions from database.

        Args:
            limit: Maximum number of questions to return

        Returns:
            List of recent Q&A records
        """
        return self.qa_repo.get_recent(limit=limit)
