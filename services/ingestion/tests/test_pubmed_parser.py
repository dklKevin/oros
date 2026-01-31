"""
Tests for PubMed XML parser.
"""

import os
import pytest

from services.ingestion.src.parsers.pubmed_xml import PubMedXMLParser
from services.ingestion.src.parsers.base import ParseError


class TestPubMedXMLParser:
    """Tests for PubMedXMLParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PubMedXMLParser()

    @pytest.fixture
    def sample_xml(self):
        """Create sample XML content."""
        return b"""<?xml version="1.0"?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.2 20190208//EN" "https://jats.nlm.nih.gov/publishing/1.2/JATS-journalpublishing1.dtd">
<article>
    <front>
        <journal-meta>
            <journal-title-group>
                <journal-title>Test Journal</journal-title>
            </journal-title-group>
        </journal-meta>
        <article-meta>
            <article-id pub-id-type="pmcid">PMC123456</article-id>
            <article-id pub-id-type="doi">10.1234/test.2024</article-id>
            <title-group>
                <article-title>Test Article Title</article-title>
            </title-group>
            <contrib-group>
                <contrib contrib-type="author">
                    <name>
                        <surname>Smith</surname>
                        <given-names>John</given-names>
                    </name>
                </contrib>
            </contrib-group>
            <pub-date pub-type="epub">
                <day>15</day>
                <month>1</month>
                <year>2024</year>
            </pub-date>
            <abstract>
                <p>This is the abstract of the test article.</p>
            </abstract>
        </article-meta>
    </front>
    <body>
        <sec>
            <title>Introduction</title>
            <p>This is the introduction section.</p>
        </sec>
        <sec>
            <title>Methods</title>
            <p>This is the methods section with detailed methodology.</p>
        </sec>
        <sec>
            <title>Results</title>
            <p>This is the results section with findings.</p>
        </sec>
    </body>
</article>
"""

    def test_can_parse_xml(self, parser):
        """Should recognize valid XML."""
        xml_content = b'<?xml version="1.0"?><article></article>'
        assert parser.can_parse(xml_content, filename="test.xml")

    def test_cannot_parse_non_xml(self, parser):
        """Should reject non-XML content."""
        pdf_content = b'%PDF-1.4'
        assert not parser.can_parse(pdf_content, filename="test.pdf")

    def test_parse_extracts_title(self, parser, sample_xml):
        """Should extract article title."""
        doc = parser.parse(sample_xml)
        assert doc.title == "Test Article Title"

    def test_parse_extracts_abstract(self, parser, sample_xml):
        """Should extract abstract."""
        doc = parser.parse(sample_xml)
        assert "abstract of the test article" in doc.abstract

    def test_parse_extracts_authors(self, parser, sample_xml):
        """Should extract authors."""
        doc = parser.parse(sample_xml)
        assert len(doc.authors) >= 1
        # Check first author
        assert doc.authors[0].surname == "Smith"
        assert doc.authors[0].given_names == "John"

    def test_parse_extracts_pmcid(self, parser, sample_xml):
        """Should extract PMC ID."""
        doc = parser.parse(sample_xml)
        assert doc.pmcid == "PMC123456"

    def test_parse_extracts_doi(self, parser, sample_xml):
        """Should extract DOI."""
        doc = parser.parse(sample_xml)
        assert doc.doi == "10.1234/test.2024"

    def test_parse_extracts_journal(self, parser, sample_xml):
        """Should extract journal name."""
        doc = parser.parse(sample_xml)
        assert doc.journal == "Test Journal"

    def test_parse_extracts_sections(self, parser, sample_xml):
        """Should extract body sections."""
        doc = parser.parse(sample_xml)
        assert len(doc.sections) >= 3
        section_titles = [s.title for s in doc.sections]
        assert "Introduction" in section_titles
        assert "Methods" in section_titles
        assert "Results" in section_titles

    def test_parse_extracts_publication_date(self, parser, sample_xml):
        """Should extract publication date."""
        doc = parser.parse(sample_xml)
        assert doc.publication_date is not None
        assert doc.publication_date.year == 2024
        assert doc.publication_date.month == 1
        assert doc.publication_date.day == 15

    def test_parse_computes_metadata(self, parser, sample_xml):
        """Should compute quality metadata."""
        doc = parser.parse(sample_xml)
        assert doc.has_abstract is True
        assert doc.has_full_text is True
        assert doc.section_count >= 3
        assert doc.word_count > 0

    def test_parse_invalid_xml_raises_error(self, parser):
        """Should raise ParseError for invalid XML."""
        invalid_xml = b"<not-closed>"
        with pytest.raises(ParseError):
            parser.parse(invalid_xml)

    def test_parse_empty_article_raises_error(self, parser):
        """Should raise ParseError for empty article."""
        empty_xml = b'<?xml version="1.0"?><article></article>'
        with pytest.raises(ParseError):
            parser.parse(empty_xml)


class TestPubMedXMLParserWithRealFile:
    """Tests using real test data files."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PubMedXMLParser()

    @pytest.fixture
    def test_file_path(self):
        """Path to a test XML file."""
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )))
        return os.path.join(base_path, "test-data", "papers", "PMC10071452.xml")

    @pytest.mark.skipif(
        not os.path.exists(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.dirname(__file__))
                ))),
                "test-data", "papers", "PMC10071452.xml"
            )
        ),
        reason="Test data file not available"
    )
    def test_parse_real_file(self, parser, test_file_path):
        """Should parse a real PubMed XML file."""
        with open(test_file_path, "rb") as f:
            content = f.read()

        doc = parser.parse(content)

        # Should have basic metadata
        assert doc.title is not None
        assert len(doc.title) > 0
        # Should have content
        assert doc.has_full_text or doc.has_abstract
