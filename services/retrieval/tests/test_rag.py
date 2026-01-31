"""
Tests for RAG service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.retrieval.src.rag import (
    RAGService,
    RAGResponse,
    Citation,
    BedrockClaudeClient,
)
from services.retrieval.src.search import SearchResult, SearchResponse


class TestBedrockClaudeClient:
    """Tests for BedrockClaudeClient."""

    def test_client_initialization(self):
        """Client should initialize with settings."""
        client = BedrockClaudeClient()
        assert client._client is None  # Lazy initialization

    def test_generate_calls_bedrock(self):
        """Generate should call Bedrock with correct parameters."""
        with patch("boto3.client") as mock_boto3_client:
            # Setup mock
            mock_client = MagicMock()
            mock_response = {
                "body": MagicMock(
                    read=MagicMock(
                        return_value=b'{"content": [{"text": "Test response"}]}'
                    )
                )
            }
            mock_client.invoke_model.return_value = mock_response
            mock_boto3_client.return_value = mock_client

            # Execute
            client = BedrockClaudeClient()
            result = client.generate("Test prompt")

            # Verify
            assert result == "Test response"
            mock_client.invoke_model.assert_called_once()


class TestRAGService:
    """Tests for RAGService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_search_results(self):
        """Create mock search results."""
        return [
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                title="Test Paper 1",
                content="CRISPR-Cas9 is a gene editing technology...",
                section_title="Introduction",
                score=0.9,
                authors=[{"given_names": "John", "surname": "Smith"}],
                journal="Nature",
                publication_date=None,
                doi="10.1234/test.1",
                pmcid="PMC123456",
            ),
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                title="Test Paper 2",
                content="Gene therapy applications include...",
                section_title="Methods",
                score=0.8,
                authors=[],
                journal="Science",
                publication_date=None,
                doi="10.1234/test.2",
                pmcid="PMC789012",
            ),
        ]

    def test_build_context_creates_citations(self, mock_db_session, mock_search_results):
        """Build context should create proper citations."""
        service = RAGService(db_session=mock_db_session)
        context, citations = service._build_context(mock_search_results)

        assert len(citations) == 2
        assert citations[0].title == "Test Paper 1"
        assert citations[0].doi == "10.1234/test.1"
        assert citations[1].title == "Test Paper 2"
        assert "Source [1]" in context
        assert "Source [2]" in context

    def test_build_prompt_includes_context(self, mock_db_session):
        """Build prompt should include context and question."""
        service = RAGService(db_session=mock_db_session)
        prompt = service._build_prompt(
            query="What is CRISPR?",
            context="CRISPR is a gene editing technology.",
            conversation_history=None,
        )

        assert "What is CRISPR?" in prompt
        assert "CRISPR is a gene editing technology" in prompt
        assert "Research paper excerpts" in prompt

    def test_build_prompt_includes_history(self, mock_db_session):
        """Build prompt should include conversation history."""
        service = RAGService(db_session=mock_db_session)
        history = [
            {"role": "user", "content": "Tell me about gene editing"},
            {"role": "assistant", "content": "Gene editing involves..."},
        ]
        prompt = service._build_prompt(
            query="What about CRISPR specifically?",
            context="CRISPR details...",
            conversation_history=history,
        )

        assert "Previous conversation" in prompt
        assert "Tell me about gene editing" in prompt

    def test_calculate_confidence_empty_chunks(self, mock_db_session):
        """Confidence should be 0 for empty chunks."""
        service = RAGService(db_session=mock_db_session)
        confidence = service._calculate_confidence([])
        assert confidence == 0.0

    def test_calculate_confidence_with_chunks(self, mock_db_session, mock_search_results):
        """Confidence should be calculated based on chunks."""
        service = RAGService(db_session=mock_db_session)
        confidence = service._calculate_confidence(mock_search_results)

        # Should be between 0 and 1
        assert 0.0 <= confidence <= 1.0
        # With 2 high-scoring chunks from different docs, should be reasonable
        assert confidence > 0.3

    @pytest.mark.asyncio
    async def test_answer_no_results(self, mock_db_session):
        """Answer should handle no search results gracefully."""
        service = RAGService(db_session=mock_db_session)

        # Create a mock search service
        mock_search = AsyncMock()
        mock_search.search = AsyncMock(
            return_value=SearchResponse(
                results=[],
                total=0,
                took_ms=10.0,
                search_type="hybrid",
            )
        )
        service._search_service = mock_search

        response = await service.answer(query="What is CRISPR?")

        assert "couldn't find" in response.answer.lower()
        assert response.confidence_score == 0.0
        assert response.chunks_used == 0

    @pytest.mark.asyncio
    async def test_answer_with_results(self, mock_db_session, mock_search_results):
        """Answer should use search results and generate response."""
        service = RAGService(db_session=mock_db_session)

        # Create mock search service
        mock_search = AsyncMock()
        mock_search.search = AsyncMock(
            return_value=SearchResponse(
                results=mock_search_results,
                total=2,
                took_ms=50.0,
                search_type="hybrid",
            )
        )
        service._search_service = mock_search

        # Create mock LLM client
        mock_llm = MagicMock()
        mock_llm.generate = MagicMock(
            return_value="CRISPR-Cas9 is a revolutionary gene editing tool [1]."
        )
        service._llm_client = mock_llm

        response = await service.answer(query="What is CRISPR?")

        assert "CRISPR" in response.answer
        assert len(response.citations) == 2
        assert response.chunks_used == 2
        assert response.confidence_score > 0


class TestCitation:
    """Tests for Citation dataclass."""

    def test_citation_creation(self):
        """Citation should be created with all fields."""
        citation = Citation(
            chunk_id=uuid4(),
            document_id=uuid4(),
            title="Test Paper",
            doi="10.1234/test",
            pmcid="PMC123456",
            relevance_score=0.95,
        )

        assert citation.title == "Test Paper"
        assert citation.doi == "10.1234/test"
        assert citation.relevance_score == 0.95

    def test_citation_optional_fields(self):
        """Citation should allow None for optional fields."""
        citation = Citation(
            chunk_id=uuid4(),
            document_id=uuid4(),
            title="Test Paper",
            doi=None,
            pmcid=None,
            relevance_score=0.8,
        )

        assert citation.doi is None
        assert citation.pmcid is None
