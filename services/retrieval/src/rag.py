"""
RAG (Retrieval-Augmented Generation) service for Oros.

Implements context retrieval and answer generation using AWS Bedrock Claude.
"""

import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import Settings, get_settings
from services.shared.logging import get_logger
from services.retrieval.src.search import SearchService, SearchFilters, SearchResult

logger = get_logger(__name__)


@dataclass
class Citation:
    """Citation for a RAG response."""

    chunk_id: UUID
    document_id: UUID
    title: str
    doi: str | None
    pmcid: str | None
    relevance_score: float


@dataclass
class RAGResponse:
    """Response from RAG query."""

    answer: str
    citations: list[Citation]
    confidence_score: float
    took_ms: float
    chunks_used: int
    model: str


class BedrockClaudeClient:
    """Client for AWS Bedrock Claude models."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = None

    def _get_client(self) -> Any:
        """Lazy initialization of Bedrock client."""
        if self._client is None:
            import boto3

            kwargs: dict[str, Any] = {
                "service_name": "bedrock-runtime",
                "region_name": self.settings.aws_region,
            }

            if self.settings.aws_endpoint_url:
                kwargs["endpoint_url"] = self.settings.aws_endpoint_url

            self._client = boto3.client(**kwargs)

        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model_id: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate a response using Claude.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            model_id: Bedrock model ID (defaults to simple model)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        client = self._get_client()
        model_id = model_id or self.settings.bedrock_llm_model_id_simple

        messages = [{"role": "user", "content": prompt}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            body["system"] = system_prompt

        try:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            content = response_body.get("content", [])

            if content and len(content) > 0:
                return content[0].get("text", "")

            return ""

        except Exception as e:
            logger.error("bedrock_llm_error", error=str(e), model=model_id)
            raise


class RAGService:
    """
    RAG service for biomedical question answering.

    Retrieves relevant document chunks and generates answers with citations.
    """

    SYSTEM_PROMPT = """You are a helpful biomedical research assistant. Your role is to answer questions about biomedical topics using the provided research paper excerpts.

Guidelines:
1. Only use information from the provided context to answer questions
2. If the context doesn't contain enough information, say so clearly
3. Always cite your sources using [1], [2], etc. corresponding to the provided chunks
4. Be precise with biomedical terminology
5. When research findings are conflicting, acknowledge both perspectives
6. Focus on facts and avoid speculation beyond what the papers state

Format your response with clear paragraphs and include citation numbers inline."""

    def __init__(
        self,
        db_session: AsyncSession,
        settings: Settings | None = None,
        llm_client: BedrockClaudeClient | None = None,
    ):
        self.db = db_session
        self.settings = settings or get_settings()
        self._llm_client = llm_client
        self._search_service = SearchService(db_session=db_session, settings=settings)

    @property
    def llm_client(self) -> BedrockClaudeClient:
        """Lazy initialization of LLM client."""
        if self._llm_client is None:
            self._llm_client = BedrockClaudeClient(self.settings)
        return self._llm_client

    async def answer(
        self,
        query: str,
        filters: SearchFilters | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        max_chunks: int = 5,
        use_complex_model: bool = False,
    ) -> RAGResponse:
        """
        Answer a question using RAG.

        Args:
            query: User's question
            filters: Optional search filters
            conversation_history: Previous messages in conversation
            max_chunks: Maximum number of chunks to retrieve
            use_complex_model: Use Sonnet instead of Haiku for complex queries

        Returns:
            RAGResponse with answer and citations
        """
        start_time = time.time()

        # Retrieve relevant chunks
        search_response = await self._search_service.search(
            query=query,
            search_type="hybrid",
            limit=max_chunks,
            filters=filters,
        )

        chunks = search_response.results

        if not chunks:
            return RAGResponse(
                answer="I couldn't find any relevant information in the knowledge base to answer your question.",
                citations=[],
                confidence_score=0.0,
                took_ms=(time.time() - start_time) * 1000,
                chunks_used=0,
                model=self.settings.bedrock_llm_model_id_simple,
            )

        # Build context and prompt
        context, citations = self._build_context(chunks)
        prompt = self._build_prompt(query, context, conversation_history)

        # Select model based on complexity
        model_id = (
            self.settings.bedrock_llm_model_id_complex
            if use_complex_model
            else self.settings.bedrock_llm_model_id_simple
        )

        # Generate answer
        try:
            answer = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                model_id=model_id,
            )
        except Exception as e:
            logger.error("rag_generation_error", error=str(e), query=query[:100])
            answer = "I encountered an error while generating the answer. Please try again."

        # Calculate confidence based on number of supporting chunks and their scores
        confidence_score = self._calculate_confidence(chunks)

        took_ms = (time.time() - start_time) * 1000

        logger.info(
            "rag_query_completed",
            query=query[:100],
            chunks_used=len(chunks),
            confidence=confidence_score,
            took_ms=took_ms,
            model=model_id,
        )

        return RAGResponse(
            answer=answer,
            citations=citations,
            confidence_score=confidence_score,
            took_ms=took_ms,
            chunks_used=len(chunks),
            model=model_id,
        )

    def _build_context(
        self,
        chunks: list[SearchResult],
    ) -> tuple[str, list[Citation]]:
        """
        Build context string and citations from search results.

        Args:
            chunks: Search results to use as context

        Returns:
            Tuple of (context string, citations list)
        """
        context_parts = []
        citations = []

        for i, chunk in enumerate(chunks, start=1):
            # Build citation
            citation = Citation(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.title,
                doi=chunk.doi,
                pmcid=chunk.pmcid,
                relevance_score=chunk.score,
            )
            citations.append(citation)

            # Build context section
            source_info = f"Source [{i}]: {chunk.title}"
            if chunk.section_title:
                source_info += f" - {chunk.section_title}"
            if chunk.doi:
                source_info += f" (DOI: {chunk.doi})"

            context_parts.append(f"{source_info}\n{chunk.content}")

        context = "\n\n---\n\n".join(context_parts)
        return context, citations

    def _build_prompt(
        self,
        query: str,
        context: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Build the user prompt with context and optional conversation history.

        Args:
            query: User's question
            context: Retrieved context
            conversation_history: Previous messages

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Add conversation history if present
        if conversation_history:
            prompt_parts.append("Previous conversation:")
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.capitalize()}: {content}")
            prompt_parts.append("")

        # Add context
        prompt_parts.append("Research paper excerpts:")
        prompt_parts.append(context)
        prompt_parts.append("")

        # Add question
        prompt_parts.append(f"Question: {query}")
        prompt_parts.append("")
        prompt_parts.append(
            "Please answer the question based on the provided excerpts. "
            "Include citation numbers [1], [2], etc. for any claims you make."
        )

        return "\n".join(prompt_parts)

    def _calculate_confidence(self, chunks: list[SearchResult]) -> float:
        """
        Calculate confidence score based on retrieved chunks.

        Higher confidence when:
        - More chunks are retrieved
        - Chunks have higher relevance scores
        - Chunks are from multiple sources

        Args:
            chunks: Retrieved search results

        Returns:
            Confidence score between 0 and 1
        """
        if not chunks:
            return 0.0

        # Average relevance score (weighted more heavily)
        avg_score = sum(c.score for c in chunks) / len(chunks)

        # Number of unique documents
        unique_docs = len(set(c.document_id for c in chunks))
        doc_diversity = min(unique_docs / 3, 1.0)  # Cap at 3 documents

        # Chunk count factor (more chunks = more evidence)
        chunk_factor = min(len(chunks) / 5, 1.0)  # Cap at 5 chunks

        # Weighted combination
        confidence = (avg_score * 0.5) + (doc_diversity * 0.3) + (chunk_factor * 0.2)

        return min(max(confidence, 0.0), 1.0)


def get_rag_service(
    db_session: AsyncSession,
    settings: Settings | None = None,
) -> RAGService:
    """Factory function to get configured RAG service."""
    return RAGService(db_session=db_session, settings=settings)
