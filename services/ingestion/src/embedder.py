"""
Embedding generation for document chunks.

Supports multiple embedding backends:
- AWS Bedrock Titan Embeddings (production)
- Local sentence-transformers (development/testing)
"""

import json
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from services.shared.config import Settings, get_settings
from services.shared.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the model identifier."""
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        pass

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        pass

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0]


class BedrockTitanEmbedder(EmbeddingProvider):
    """
    AWS Bedrock Titan Embeddings provider.

    Uses amazon.titan-embed-text-v1 model (1536 dimensions).
    """

    MODEL_ID = "amazon.titan-embed-text-v1"
    DIMENSIONS = 1536
    MAX_TOKENS = 8192

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = None

    @property
    def model_id(self) -> str:
        return self.MODEL_ID

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS

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

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Bedrock Titan."""
        client = self._get_client()
        embeddings = []

        for text in texts:
            try:
                # Truncate if necessary (Titan has 8K token limit)
                if len(text) > 30000:  # Rough char estimate
                    text = text[:30000]

                body = json.dumps({"inputText": text})

                response = client.invoke_model(
                    modelId=self.MODEL_ID,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )

                response_body = json.loads(response["body"].read())
                embedding = response_body["embedding"]
                embeddings.append(embedding)

            except Exception as e:
                logger.error("bedrock_embedding_error", error=str(e), text_length=len(text))
                # Return zero vector on error (will be filtered out later)
                embeddings.append([0.0] * self.DIMENSIONS)

        logger.info(
            "embeddings_generated",
            provider="bedrock",
            count=len(embeddings),
            model=self.MODEL_ID,
        )

        return embeddings


class LocalEmbedder(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.

    Uses all-MiniLM-L6-v2 by default (384 dimensions).
    Can also use larger models for better quality.
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    DIMENSIONS_MAP = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "multi-qa-mpnet-base-dot-v1": 768,
    }

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or self.DEFAULT_MODEL
        self._model = None
        self._dimensions = self.DIMENSIONS_MAP.get(self._model_name, 384)

    @property
    def model_id(self) -> str:
        return f"sentence-transformers/{self._model_name}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _get_model(self) -> Any:
        """Lazy initialization of sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self._model_name)
                # Update dimensions from actual model
                self._dimensions = self._model.get_sentence_embedding_dimension()
                logger.info(
                    "local_model_loaded",
                    model=self._model_name,
                    dimensions=self._dimensions,
                )
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using local sentence-transformers."""
        model = self._get_model()

        try:
            # Generate embeddings
            embeddings = model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True,  # Normalize for cosine similarity
            )

            # Convert to list of lists
            result = [emb.tolist() for emb in embeddings]

            logger.info(
                "embeddings_generated",
                provider="local",
                count=len(result),
                model=self._model_name,
            )

            return result

        except Exception as e:
            logger.error("local_embedding_error", error=str(e))
            raise


class PaddedLocalEmbedder(LocalEmbedder):
    """
    Local embedder that pads embeddings to 1536 dimensions.

    Useful for development when using local models but wanting
    to match the Bedrock Titan embedding dimension for compatibility.
    """

    TARGET_DIMENSIONS = 1536

    @property
    def dimensions(self) -> int:
        return self.TARGET_DIMENSIONS

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings and pad to target dimensions."""
        # Get base embeddings
        base_embeddings = super().embed(texts)

        # Pad to target dimensions
        padded = []
        for emb in base_embeddings:
            if len(emb) < self.TARGET_DIMENSIONS:
                # Pad with zeros
                padded_emb = emb + [0.0] * (self.TARGET_DIMENSIONS - len(emb))
            else:
                # Truncate if somehow larger
                padded_emb = emb[: self.TARGET_DIMENSIONS]
            padded.append(padded_emb)

        return padded


class Embedder:
    """
    Main embedder class that manages embedding generation.

    Automatically selects the appropriate provider based on configuration.
    """

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()

        if provider:
            self._provider = provider
        elif self.settings.is_development and not self.settings.aws_access_key_id:
            # Use padded local embedder in development without AWS credentials
            logger.info("using_local_embedder", reason="no_aws_credentials")
            self._provider = PaddedLocalEmbedder()
        else:
            # Use Bedrock in production or when AWS is configured
            self._provider = BedrockTitanEmbedder(self.settings)

    @property
    def model_id(self) -> str:
        """Get the current model ID."""
        return self._provider.model_id

    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions."""
        return self._provider.dimensions

    def embed_chunks(
        self,
        chunks: list[Any],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of chunks.

        Args:
            chunks: List of Chunk objects with content attribute
            batch_size: Number of chunks to process at once

        Returns:
            List of embedding vectors
        """
        texts = [chunk.content for chunk in chunks]
        return self.embed_texts(texts, batch_size=batch_size)

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings
            batch_size: Number of texts to process at once

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self._provider.embed(batch)
            all_embeddings.extend(batch_embeddings)

            logger.debug(
                "embedding_batch_complete",
                batch_start=i,
                batch_size=len(batch),
                total=len(texts),
            )

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Embedding vector
        """
        return self._provider.embed_single(query)


def get_embedder(settings: Settings | None = None) -> Embedder:
    """Factory function to get configured embedder."""
    return Embedder(settings=settings)
