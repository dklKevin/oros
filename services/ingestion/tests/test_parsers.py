"""
Tests for document parsers.
"""

import pytest
from datetime import date

from services.ingestion.src.parsers.base import (
    ParsedDocument,
    Section,
    Author,
    ParseError,
)


class TestSection:
    """Tests for Section dataclass."""

    def test_section_creation(self):
        """Section should be created with required fields."""
        section = Section(title="Introduction", content="Test content")
        assert section.title == "Introduction"
        assert section.content == "Test content"

    def test_section_with_type(self):
        """Section should accept section_type."""
        section = Section(
            title="Methods",
            content="Methods content",
            section_type="methods",
        )
        assert section.section_type == "methods"

    def test_section_with_subsections(self):
        """Section should accept subsections."""
        subsection = Section(title="Sub", content="Sub content")
        section = Section(
            title="Main",
            content="Main content",
            subsections=[subsection],
        )
        assert len(section.subsections) == 1
        assert section.subsections[0].title == "Sub"


class TestAuthor:
    """Tests for Author dataclass."""

    def test_author_creation(self):
        """Author should be created with required fields."""
        author = Author(given_names="John", surname="Smith")
        assert author.given_names == "John"
        assert author.surname == "Smith"

    def test_author_with_optional_fields(self):
        """Author should accept optional fields."""
        author = Author(
            given_names="Jane",
            surname="Doe",
            email="jane@example.com",
            affiliations=["MIT", "Stanford"],
            orcid="0000-0001-2345-6789",
        )
        assert author.email == "jane@example.com"
        assert len(author.affiliations) == 2
        assert author.orcid == "0000-0001-2345-6789"


class TestParsedDocument:
    """Tests for ParsedDocument dataclass."""

    @pytest.fixture
    def minimal_doc(self):
        """Create a minimal document."""
        return ParsedDocument(
            title="Test Paper",
            abstract=None,
            sections=[],
            full_text="Test content",
            authors=[],
            journal=None,
            publication_date=None,
            doi=None,
            pmcid=None,
            pmid=None,
        )

    @pytest.fixture
    def full_doc(self):
        """Create a document with all fields."""
        return ParsedDocument(
            title="Complete Paper",
            abstract="This is the abstract.",
            sections=[
                Section(title="Intro", content="Introduction content"),
                Section(title="Methods", content="Methods content"),
            ],
            full_text="Full text of the paper goes here with many words.",
            authors=[
                Author(given_names="John", surname="Smith"),
                Author(given_names="Jane", surname="Doe"),
            ],
            journal="Nature",
            publication_date=date(2024, 1, 15),
            doi="10.1234/test.2024",
            pmcid="PMC123456",
            pmid="12345678",
            mesh_terms=["Gene Editing", "CRISPR"],
            keywords=["genetics", "biotechnology"],
            article_type="research-article",
        )

    def test_minimal_doc_creation(self, minimal_doc):
        """Minimal document should be created successfully."""
        assert minimal_doc.title == "Test Paper"
        assert minimal_doc.abstract is None
        assert len(minimal_doc.sections) == 0

    def test_full_doc_creation(self, full_doc):
        """Full document should be created with all fields."""
        assert full_doc.title == "Complete Paper"
        assert full_doc.abstract == "This is the abstract."
        assert len(full_doc.sections) == 2
        assert len(full_doc.authors) == 2
        assert full_doc.journal == "Nature"
        assert full_doc.doi == "10.1234/test.2024"

    def test_has_abstract_computed(self, minimal_doc, full_doc):
        """has_abstract should be computed based on abstract presence."""
        assert minimal_doc.has_abstract is False
        assert full_doc.has_abstract is True

    def test_has_full_text_computed(self, minimal_doc, full_doc):
        """has_full_text should be computed based on sections."""
        assert minimal_doc.has_full_text is False
        assert full_doc.has_full_text is True

    def test_section_count_computed(self, minimal_doc, full_doc):
        """section_count should be computed from sections list."""
        assert minimal_doc.section_count == 0
        assert full_doc.section_count == 2

    def test_word_count_computed(self, full_doc):
        """word_count should be computed from full_text."""
        assert full_doc.word_count > 0
        # "Full text of the paper goes here with many words." = 10 words
        assert full_doc.word_count == 10


class TestParseError:
    """Tests for ParseError exception."""

    def test_parse_error_message(self):
        """ParseError should have a message."""
        error = ParseError("Failed to parse document")
        assert str(error) == "Failed to parse document"

    def test_parse_error_with_details(self):
        """ParseError should accept details."""
        error = ParseError(
            "Parse failed",
            details={"line": 42, "reason": "Invalid XML"},
        )
        assert error.details["line"] == 42
        assert error.details["reason"] == "Invalid XML"

    def test_parse_error_default_details(self):
        """ParseError should have empty details by default."""
        error = ParseError("Error")
        assert error.details == {}


class TestParserRegistry:
    """Tests for parser module exports and factory patterns."""

    def test_parser_module_exports_all_parsers(self):
        """Parser module should export all parser classes."""
        from services.ingestion.src.parsers import (
            BaseParser,
            ParsedDocument,
            ParseError,
            PDFParser,
            PubMedXMLParser,
        )
        # Verify all exports are classes
        assert BaseParser is not None
        assert ParsedDocument is not None
        assert ParseError is not None
        assert PDFParser is not None
        assert PubMedXMLParser is not None

    def test_pdf_parser_inherits_from_base(self):
        """PDFParser should inherit from BaseParser."""
        from services.ingestion.src.parsers import BaseParser, PDFParser
        parser = PDFParser()
        assert isinstance(parser, BaseParser)

    def test_pubmed_parser_inherits_from_base(self):
        """PubMedXMLParser should inherit from BaseParser."""
        from services.ingestion.src.parsers import BaseParser, PubMedXMLParser
        parser = PubMedXMLParser()
        assert isinstance(parser, BaseParser)

    def test_parser_can_parse_mutual_exclusion(self):
        """Parsers should correctly identify their format and reject others."""
        from services.ingestion.src.parsers import PDFParser, PubMedXMLParser

        pdf_parser = PDFParser()
        xml_parser = PubMedXMLParser()

        pdf_content = b"%PDF-1.4\n..."
        xml_content = b'<?xml version="1.0"?><article></article>'

        # PDF parser should accept PDF and reject XML
        assert pdf_parser.can_parse(pdf_content)
        assert not pdf_parser.can_parse(xml_content)

        # XML parser should accept XML and reject PDF
        assert xml_parser.can_parse(xml_content)
        assert not xml_parser.can_parse(pdf_content)
