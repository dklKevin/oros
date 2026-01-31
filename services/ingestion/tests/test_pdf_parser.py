"""
Tests for PDF parser.

Following TDD methodology: these tests are written FIRST before implementation.
"""

import pytest

from services.ingestion.src.parsers.pdf import PDFParser
from services.ingestion.src.parsers.base import ParseError


class TestPDFParserCanParse:
    """Tests for PDFParser.can_parse method."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    def test_can_parse_pdf_by_magic_bytes(self, parser: PDFParser) -> None:
        """Should recognize PDF by magic bytes (%PDF-)."""
        pdf_header = b"%PDF-1.4\n"
        assert parser.can_parse(pdf_header, filename=None)

    def test_can_parse_pdf_by_filename(self, parser: PDFParser) -> None:
        """Should recognize PDF by filename extension."""
        # Even with minimal content, filename should help identify
        content = b"some binary content"
        assert parser.can_parse(content, filename="document.pdf")

    def test_cannot_parse_xml(self, parser: PDFParser) -> None:
        """Should reject XML content."""
        xml_content = b'<?xml version="1.0"?><article></article>'
        assert not parser.can_parse(xml_content, filename="test.xml")

    def test_cannot_parse_html(self, parser: PDFParser) -> None:
        """Should reject HTML content."""
        html_content = b"<!DOCTYPE html><html><body>Hello</body></html>"
        assert not parser.can_parse(html_content, filename="test.html")

    def test_cannot_parse_random_bytes(self, parser: PDFParser) -> None:
        """Should reject random binary content."""
        random_content = b"\x00\x01\x02\x03\x04\x05"
        assert not parser.can_parse(random_content, filename=None)


class TestPDFParserBasicParsing:
    """Tests for basic PDF parsing functionality."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    @pytest.fixture
    def minimal_pdf_content(self) -> bytes:
        """
        Create minimal valid PDF content for testing.
        This is a simple 1-page PDF with text "Test Document Title".
        """
        # We'll need to create a real minimal PDF for testing
        # This uses PyMuPDF to generate test content
        import fitz

        doc = fitz.open()  # Create new PDF
        page = doc.new_page()

        # Add title text
        title_rect = fitz.Rect(50, 50, 550, 100)
        page.insert_textbox(title_rect, "Test Document Title", fontsize=18)

        # Add abstract
        abstract_rect = fitz.Rect(50, 120, 550, 200)
        page.insert_textbox(
            abstract_rect,
            "Abstract: This is a test abstract for the PDF parser. "
            "It contains important information about the research.",
            fontsize=10,
        )

        # Add body text
        body_rect = fitz.Rect(50, 220, 550, 600)
        page.insert_textbox(
            body_rect,
            "Introduction\n\n"
            "This section introduces the research topic. We discuss background "
            "information and the motivation for this study.\n\n"
            "Methods\n\n"
            "The methodology involves several steps including data collection "
            "and analysis using various techniques.\n\n"
            "Results\n\n"
            "Our findings show significant improvements in the treatment group.",
            fontsize=10,
        )

        # Return as bytes
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_parse_returns_parsed_document(
        self, parser: PDFParser, minimal_pdf_content: bytes
    ) -> None:
        """Should return a ParsedDocument instance."""
        doc = parser.parse(minimal_pdf_content)

        from services.ingestion.src.parsers.base import ParsedDocument
        assert isinstance(doc, ParsedDocument)

    def test_parse_extracts_title(
        self, parser: PDFParser, minimal_pdf_content: bytes
    ) -> None:
        """Should extract document title from first large text."""
        doc = parser.parse(minimal_pdf_content)
        assert doc.title is not None
        assert len(doc.title) > 0

    def test_parse_extracts_full_text(
        self, parser: PDFParser, minimal_pdf_content: bytes
    ) -> None:
        """Should extract full text content."""
        doc = parser.parse(minimal_pdf_content)
        assert doc.full_text is not None
        assert len(doc.full_text) > 50  # Should have substantial content

    def test_parse_computes_word_count(
        self, parser: PDFParser, minimal_pdf_content: bytes
    ) -> None:
        """Should compute word count."""
        doc = parser.parse(minimal_pdf_content)
        assert doc.word_count > 0


class TestPDFParserSectionExtraction:
    """Tests for section extraction from PDFs."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    @pytest.fixture
    def biomedical_pdf_content(self) -> bytes:
        """Create PDF with biomedical paper structure."""
        import fitz

        doc = fitz.open()

        # Page 1: Title and Abstract
        page = doc.new_page()
        page.insert_textbox(
            fitz.Rect(50, 50, 550, 90),
            "CRISPR-Cas9 Gene Editing for Cardiovascular Disease Treatment",
            fontsize=16,
        )
        page.insert_textbox(
            fitz.Rect(50, 100, 550, 130),
            "John Smith, Jane Doe, Robert Johnson",
            fontsize=10,
        )
        page.insert_textbox(
            fitz.Rect(50, 140, 550, 180),
            "Nature Biotechnology | DOI: 10.1038/test.2024.001",
            fontsize=9,
        )
        page.insert_textbox(
            fitz.Rect(50, 200, 550, 250),
            "Abstract",
            fontsize=12,
        )
        page.insert_textbox(
            fitz.Rect(50, 260, 550, 400),
            "This study investigates the application of CRISPR-Cas9 gene editing "
            "technology for treating cardiovascular diseases. We demonstrate "
            "successful gene modification in cardiac tissue samples and show "
            "promising therapeutic outcomes.",
            fontsize=10,
        )

        # Page 2: Introduction and Methods
        page2 = doc.new_page()
        page2.insert_textbox(
            fitz.Rect(50, 50, 550, 80),
            "Introduction",
            fontsize=12,
        )
        page2.insert_textbox(
            fitz.Rect(50, 90, 550, 250),
            "Cardiovascular disease remains the leading cause of mortality worldwide. "
            "Recent advances in gene editing technologies, particularly CRISPR-Cas9, "
            "offer new therapeutic possibilities. This technology enables precise "
            "modifications to the genome, potentially correcting genetic defects "
            "responsible for inherited cardiac conditions.",
            fontsize=10,
        )
        page2.insert_textbox(
            fitz.Rect(50, 270, 550, 300),
            "Methods",
            fontsize=12,
        )
        page2.insert_textbox(
            fitz.Rect(50, 310, 550, 500),
            "We employed CRISPR-Cas9 with custom guide RNAs targeting specific "
            "genetic loci associated with familial hypercholesterolemia. Cardiac "
            "tissue samples were obtained from consenting patients undergoing "
            "bypass surgery. Gene editing efficiency was measured using next-generation "
            "sequencing approaches.",
            fontsize=10,
        )

        # Page 3: Results and Discussion
        page3 = doc.new_page()
        page3.insert_textbox(
            fitz.Rect(50, 50, 550, 80),
            "Results",
            fontsize=12,
        )
        page3.insert_textbox(
            fitz.Rect(50, 90, 550, 250),
            "Our CRISPR-Cas9 approach achieved 78% editing efficiency in targeted "
            "cardiomyocytes. Off-target analysis revealed minimal unintended "
            "modifications. Treated cells showed normalized lipid metabolism "
            "markers within 72 hours post-editing.",
            fontsize=10,
        )
        page3.insert_textbox(
            fitz.Rect(50, 270, 550, 300),
            "Discussion",
            fontsize=12,
        )
        page3.insert_textbox(
            fitz.Rect(50, 310, 550, 500),
            "These findings demonstrate the potential of CRISPR-Cas9 for treating "
            "genetic cardiovascular diseases. The high editing efficiency and low "
            "off-target effects support further development toward clinical trials.",
            fontsize=10,
        )

        # Page 4: References
        page4 = doc.new_page()
        page4.insert_textbox(
            fitz.Rect(50, 50, 550, 80),
            "References",
            fontsize=12,
        )
        page4.insert_textbox(
            fitz.Rect(50, 90, 550, 400),
            "1. Doudna JA, Charpentier E. The new frontier of genome engineering "
            "with CRISPR-Cas9. Science. 2014;346(6213):1258096.\n"
            "2. Musunuru K. Genome editing of human pluripotent stem cells to "
            "generate human cellular disease models. Dis Model Mech. 2013;6(4):896-904.\n"
            "3. Smith JG et al. Cardiovascular gene therapy approaches. Nat Rev "
            "Cardiol. 2020;17(4):214-229.",
            fontsize=9,
        )

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_parse_identifies_abstract(
        self, parser: PDFParser, biomedical_pdf_content: bytes
    ) -> None:
        """Should identify and extract abstract section."""
        doc = parser.parse(biomedical_pdf_content)
        assert doc.abstract is not None
        assert "CRISPR" in doc.abstract or "investigates" in doc.abstract

    def test_parse_extracts_sections(
        self, parser: PDFParser, biomedical_pdf_content: bytes
    ) -> None:
        """Should extract named sections from the document."""
        doc = parser.parse(biomedical_pdf_content)
        assert len(doc.sections) > 0

        section_titles = [s.title.lower() for s in doc.sections]
        # Should have at least some standard sections
        found_sections = sum(1 for title in section_titles
                           if any(kw in title for kw in
                                  ['introduction', 'method', 'result', 'discussion']))
        assert found_sections >= 2

    def test_parse_assigns_section_types(
        self, parser: PDFParser, biomedical_pdf_content: bytes
    ) -> None:
        """Should assign section_type to recognized sections."""
        doc = parser.parse(biomedical_pdf_content)

        # At least some sections should have types
        typed_sections = [s for s in doc.sections if s.section_type is not None]
        assert len(typed_sections) > 0


class TestPDFParserMetadataExtraction:
    """Tests for metadata extraction from PDFs."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    @pytest.fixture
    def pdf_with_metadata(self) -> bytes:
        """Create PDF with embedded metadata."""
        import fitz

        doc = fitz.open()

        # Set PDF metadata
        doc.set_metadata({
            "title": "Gene Therapy Research Paper",
            "author": "Dr. Alice Researcher, Dr. Bob Scientist",
            "subject": "Biomedical Research",
            "keywords": "gene therapy, CRISPR, cardiovascular",
            "creator": "Test PDF Generator",
            "producer": "PyMuPDF",
        })

        page = doc.new_page()
        page.insert_textbox(
            fitz.Rect(50, 50, 550, 100),
            "Gene Therapy Research Paper",
            fontsize=16,
        )
        page.insert_textbox(
            fitz.Rect(50, 120, 550, 300),
            "This paper discusses advances in gene therapy for treating "
            "various genetic disorders.",
            fontsize=10,
        )

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_parse_extracts_pdf_metadata_title(
        self, parser: PDFParser, pdf_with_metadata: bytes
    ) -> None:
        """Should extract title from PDF metadata."""
        doc = parser.parse(pdf_with_metadata)
        # Title should come from metadata or first heading
        assert doc.title is not None
        assert "gene therapy" in doc.title.lower() or "research" in doc.title.lower()

    def test_parse_extracts_keywords_from_metadata(
        self, parser: PDFParser, pdf_with_metadata: bytes
    ) -> None:
        """Should extract keywords from PDF metadata."""
        doc = parser.parse(pdf_with_metadata)
        # Keywords may be in keywords list
        assert len(doc.keywords) > 0 or "crispr" in doc.full_text.lower()


class TestPDFParserAuthorExtraction:
    """Tests for author extraction from PDFs."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    @pytest.fixture
    def pdf_with_authors(self) -> bytes:
        """Create PDF with author information."""
        import fitz

        doc = fitz.open()
        doc.set_metadata({
            "author": "John Smith; Jane Doe; Robert Johnson",
        })

        page = doc.new_page()
        page.insert_textbox(
            fitz.Rect(50, 50, 550, 90),
            "Advances in CRISPR Technology",
            fontsize=16,
        )
        page.insert_textbox(
            fitz.Rect(50, 100, 550, 130),
            "John Smith¹, Jane Doe², Robert Johnson¹*",
            fontsize=10,
        )
        page.insert_textbox(
            fitz.Rect(50, 140, 550, 180),
            "¹ Department of Biology, Stanford University\n"
            "² Department of Medicine, Harvard Medical School",
            fontsize=8,
        )
        page.insert_textbox(
            fitz.Rect(50, 200, 550, 400),
            "Abstract: This paper presents advances in CRISPR technology.",
            fontsize=10,
        )

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_parse_extracts_authors(
        self, parser: PDFParser, pdf_with_authors: bytes
    ) -> None:
        """Should extract author list from PDF."""
        doc = parser.parse(pdf_with_authors)
        # Should have some authors (from metadata or text parsing)
        assert len(doc.authors) >= 1

    def test_parse_extracts_author_names(
        self, parser: PDFParser, pdf_with_authors: bytes
    ) -> None:
        """Should extract author given names and surnames."""
        doc = parser.parse(pdf_with_authors)
        if doc.authors:
            # At least one author should have a surname
            assert any(a.surname for a in doc.authors)


class TestPDFParserReferenceExtraction:
    """Tests for reference extraction from PDFs."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    @pytest.fixture
    def pdf_with_references(self) -> bytes:
        """Create PDF with references section."""
        import fitz

        doc = fitz.open()

        page = doc.new_page()
        page.insert_textbox(
            fitz.Rect(50, 50, 550, 90),
            "Research Paper",
            fontsize=16,
        )
        page.insert_textbox(
            fitz.Rect(50, 100, 550, 250),
            "This paper discusses important research findings.",
            fontsize=10,
        )
        page.insert_textbox(
            fitz.Rect(50, 270, 550, 300),
            "References",
            fontsize=12,
        )
        page.insert_textbox(
            fitz.Rect(50, 310, 550, 700),
            "[1] Smith J, Doe J. Introduction to Gene Editing. Nature. 2020;580:234-240. "
            "doi:10.1038/s41586-020-2157-4\n\n"
            "[2] Johnson R et al. CRISPR Applications in Medicine. Science. 2021;371:556-560.\n\n"
            "[3] Williams A. Cardiovascular Gene Therapy. Circulation. 2022;145:1234-1240. "
            "PMID: 12345678",
            fontsize=9,
        )

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_parse_extracts_references(
        self, parser: PDFParser, pdf_with_references: bytes
    ) -> None:
        """Should extract references from the document."""
        doc = parser.parse(pdf_with_references)
        # Should have at least some references
        assert len(doc.references) >= 1

    def test_parse_extracts_reference_details(
        self, parser: PDFParser, pdf_with_references: bytes
    ) -> None:
        """Should extract details from references (title, year, etc.)."""
        doc = parser.parse(pdf_with_references)
        if doc.references:
            # At least one reference should have some content
            ref = doc.references[0]
            assert isinstance(ref, dict)


class TestPDFParserDOIExtraction:
    """Tests for DOI extraction from PDFs."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    @pytest.fixture
    def pdf_with_doi(self) -> bytes:
        """Create PDF containing DOI."""
        import fitz

        doc = fitz.open()

        page = doc.new_page()
        page.insert_textbox(
            fitz.Rect(50, 50, 550, 90),
            "Research Article",
            fontsize=16,
        )
        page.insert_textbox(
            fitz.Rect(50, 100, 550, 130),
            "DOI: 10.1038/s41586-024-07089-w",
            fontsize=9,
        )
        page.insert_textbox(
            fitz.Rect(50, 140, 550, 300),
            "This paper presents novel findings.",
            fontsize=10,
        )

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_parse_extracts_doi(
        self, parser: PDFParser, pdf_with_doi: bytes
    ) -> None:
        """Should extract DOI from PDF content."""
        doc = parser.parse(pdf_with_doi)
        assert doc.doi is not None
        assert doc.doi.startswith("10.")


class TestPDFParserErrorHandling:
    """Tests for error handling in PDF parser."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    def test_parse_invalid_pdf_raises_error(self, parser: PDFParser) -> None:
        """Should raise ParseError for invalid PDF content."""
        invalid_content = b"This is not a PDF file"
        with pytest.raises(ParseError):
            parser.parse(invalid_content)

    def test_parse_empty_content_raises_error(self, parser: PDFParser) -> None:
        """Should raise ParseError for empty content."""
        with pytest.raises(ParseError):
            parser.parse(b"")

    def test_parse_corrupted_pdf_raises_error(self, parser: PDFParser) -> None:
        """Should raise ParseError for corrupted PDF."""
        corrupted = b"%PDF-1.4\n%%EOF"  # Invalid PDF structure
        with pytest.raises(ParseError):
            parser.parse(corrupted)


class TestPDFParserQualityMetrics:
    """Tests for quality metrics computation."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create a parser instance."""
        return PDFParser()

    @pytest.fixture
    def complete_pdf(self) -> bytes:
        """Create a complete PDF with all sections."""
        import fitz

        doc = fitz.open()

        # Multiple pages with full content
        for i, (title, content) in enumerate([
            ("Title Page", "Research Paper Title\nAuthors: A, B, C"),
            ("Abstract", "This is a comprehensive abstract of the research."),
            ("Introduction", "Background and motivation for the study."),
            ("Methods", "Detailed methodology description."),
            ("Results", "Key findings and data analysis."),
            ("Discussion", "Interpretation of results."),
            ("Conclusion", "Summary and future directions."),
        ]):
            page = doc.new_page()
            page.insert_textbox(fitz.Rect(50, 50, 550, 80), title, fontsize=14)
            page.insert_textbox(fitz.Rect(50, 100, 550, 700), content, fontsize=10)

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_parse_sets_has_abstract(
        self, parser: PDFParser, complete_pdf: bytes
    ) -> None:
        """Should set has_abstract flag correctly."""
        doc = parser.parse(complete_pdf)
        # The __post_init__ should set this based on abstract content
        assert doc.has_abstract == (doc.abstract is not None and len(doc.abstract) > 0)

    def test_parse_sets_has_full_text(
        self, parser: PDFParser, complete_pdf: bytes
    ) -> None:
        """Should set has_full_text flag based on sections."""
        doc = parser.parse(complete_pdf)
        assert doc.has_full_text == (len(doc.sections) > 0)

    def test_parse_computes_section_count(
        self, parser: PDFParser, complete_pdf: bytes
    ) -> None:
        """Should compute section_count correctly."""
        doc = parser.parse(complete_pdf)
        assert doc.section_count == len(doc.sections)
