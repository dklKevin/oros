"""
Base parser interface and common data structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Section:
    """Represents a section of a document."""

    title: str
    content: str
    section_type: str | None = None  # introduction, methods, results, discussion, etc.
    subsections: list["Section"] = field(default_factory=list)


@dataclass
class Author:
    """Represents an author of a document."""

    given_names: str
    surname: str
    email: str | None = None
    affiliations: list[str] = field(default_factory=list)
    orcid: str | None = None


@dataclass
class ParsedDocument:
    """
    Represents a fully parsed document.

    This is the common output format for all parsers.
    """

    # Core content
    title: str
    abstract: str | None
    sections: list[Section]
    full_text: str  # Concatenated full text for fallback

    # Metadata
    authors: list[Author]
    journal: str | None
    publication_date: date | None

    # Identifiers
    doi: str | None
    pmcid: str | None
    pmid: str | None

    # Classification
    mesh_terms: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    article_type: str | None = None

    # References
    references: list[dict[str, Any]] = field(default_factory=list)

    # Quality indicators
    has_abstract: bool = False
    has_full_text: bool = False
    section_count: int = 0
    word_count: int = 0

    # Raw metadata for debugging
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute derived fields after initialization."""
        self.has_abstract = bool(self.abstract)
        self.has_full_text = bool(self.sections)
        self.section_count = len(self.sections)
        self.word_count = len(self.full_text.split())


class BaseParser(ABC):
    """
    Abstract base class for document parsers.

    All parsers must implement the parse method.
    """

    @abstractmethod
    def parse(self, content: bytes) -> ParsedDocument:
        """
        Parse document content into a structured ParsedDocument.

        Args:
            content: Raw document content as bytes

        Returns:
            ParsedDocument with extracted content and metadata

        Raises:
            ParseError: If the document cannot be parsed
        """
        pass

    @abstractmethod
    def can_parse(self, content: bytes, filename: str | None = None) -> bool:
        """
        Check if this parser can handle the given content.

        Args:
            content: Raw document content as bytes
            filename: Optional filename for format detection

        Returns:
            True if this parser can handle the content
        """
        pass


class ParseError(Exception):
    """Raised when a document cannot be parsed."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}
