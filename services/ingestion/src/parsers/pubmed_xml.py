"""
PubMed XML Parser for PubMed Central Open Access articles.

Parses PMC XML format and extracts structured content including:
- Title, abstract, full text sections
- Authors with affiliations
- Journal metadata
- MeSH terms and keywords
- References
"""

from datetime import date
from typing import Any

from lxml import etree

from services.shared.logging import get_logger
from services.ingestion.src.parsers.base import (
    Author,
    BaseParser,
    ParsedDocument,
    ParseError,
    Section,
)

logger = get_logger(__name__)


class PubMedXMLParser(BaseParser):
    """Parser for PubMed Central XML format."""

    # XML namespaces used in PMC articles
    NAMESPACES = {
        "mml": "http://www.w3.org/1998/Math/MathML",
        "xlink": "http://www.w3.org/1999/xlink",
    }

    # Section type mappings
    SECTION_TYPE_MAP = {
        "intro": "introduction",
        "introduction": "introduction",
        "background": "introduction",
        "methods": "methods",
        "materials and methods": "methods",
        "materials|methods": "methods",
        "experimental": "methods",
        "results": "results",
        "findings": "results",
        "discussion": "discussion",
        "conclusions": "conclusion",
        "conclusion": "conclusion",
        "summary": "conclusion",
        "abstract": "abstract",
        "references": "references",
        "supplementary": "supplementary",
        "acknowledgments": "acknowledgments",
        "acknowledgements": "acknowledgments",
    }

    def can_parse(self, content: bytes, filename: str | None = None) -> bool:
        """Check if content is PubMed XML format."""
        try:
            # Check for XML declaration and PMC-specific elements
            content_str = content[:2000].decode("utf-8", errors="ignore").lower()
            return (
                "<?xml" in content_str
                and ("pmc-articleset" in content_str or "<article" in content_str)
            )
        except Exception:
            return False

    def parse(self, content: bytes) -> ParsedDocument:
        """
        Parse PubMed XML content into a structured document.

        Args:
            content: Raw XML content as bytes

        Returns:
            ParsedDocument with extracted content

        Raises:
            ParseError: If XML cannot be parsed
        """
        try:
            # Parse XML
            root = etree.fromstring(content)

            # Find the article element
            article = root.find(".//article")
            if article is None:
                article = root  # Root might be the article itself

            # Extract metadata
            front = article.find(".//front")
            if front is None:
                raise ParseError("No front matter found in article")

            article_meta = front.find(".//article-meta")
            if article_meta is None:
                raise ParseError("No article-meta found")

            # Extract core fields
            title = self._extract_title(article_meta)
            abstract = self._extract_abstract(article_meta)
            authors = self._extract_authors(article_meta)
            journal = self._extract_journal(front)
            pub_date = self._extract_publication_date(article_meta)

            # Extract identifiers
            doi = self._extract_id(article_meta, "doi")
            pmcid = self._extract_id(article_meta, "pmcid") or self._extract_id(article_meta, "pmc")
            pmid = self._extract_id(article_meta, "pmid")

            # Extract classification
            mesh_terms = self._extract_mesh_terms(article_meta)
            keywords = self._extract_keywords(article_meta)
            article_type = self._extract_article_type(article)

            # Extract body sections
            body = article.find(".//body")
            sections = self._extract_sections(body) if body is not None else []

            # Extract references
            back = article.find(".//back")
            references = self._extract_references(back) if back is not None else []

            # Build full text
            full_text = self._build_full_text(title, abstract, sections)

            return ParsedDocument(
                title=title,
                abstract=abstract,
                sections=sections,
                full_text=full_text,
                authors=authors,
                journal=journal,
                publication_date=pub_date,
                doi=doi,
                pmcid=pmcid,
                pmid=pmid,
                mesh_terms=mesh_terms,
                keywords=keywords,
                article_type=article_type,
                references=references,
                raw_metadata={
                    "parser": "pubmed_xml",
                    "version": "1.0",
                },
            )

        except etree.XMLSyntaxError as e:
            logger.error("xml_parse_error", error=str(e))
            raise ParseError(f"Invalid XML: {e}", {"xml_error": str(e)})
        except Exception as e:
            logger.error("parse_error", error=str(e))
            raise ParseError(f"Failed to parse document: {e}")

    def _extract_title(self, article_meta: etree._Element) -> str:
        """Extract article title."""
        title_group = article_meta.find(".//title-group")
        if title_group is not None:
            title_elem = title_group.find(".//article-title")
            if title_elem is not None:
                return self._get_text_content(title_elem)
        return "Untitled"

    def _extract_abstract(self, article_meta: etree._Element) -> str | None:
        """Extract article abstract."""
        abstract = article_meta.find(".//abstract")
        if abstract is not None:
            # Handle structured abstracts with sections
            sections = abstract.findall(".//sec")
            if sections:
                parts = []
                for sec in sections:
                    title = sec.find(".//title")
                    title_text = self._get_text_content(title) if title is not None else ""
                    content = " ".join(
                        self._get_text_content(p) for p in sec.findall(".//p")
                    )
                    if title_text:
                        parts.append(f"{title_text}: {content}")
                    else:
                        parts.append(content)
                return " ".join(parts)
            else:
                # Simple abstract
                return self._get_text_content(abstract)
        return None

    def _extract_authors(self, article_meta: etree._Element) -> list[Author]:
        """Extract author information."""
        authors = []
        contrib_group = article_meta.find(".//contrib-group")

        if contrib_group is None:
            return authors

        # Build affiliation map
        aff_map = {}
        for aff in article_meta.findall(".//aff"):
            aff_id = aff.get("id", "")
            aff_text = self._get_text_content(aff)
            if aff_id:
                aff_map[aff_id] = aff_text

        for contrib in contrib_group.findall(".//contrib"):
            if contrib.get("contrib-type") != "author":
                continue

            name_elem = contrib.find(".//name")
            if name_elem is None:
                continue

            surname = name_elem.findtext("surname", "")
            given_names = name_elem.findtext("given-names", "")

            # Get email
            email = contrib.findtext(".//email")

            # Get ORCID
            orcid = None
            contrib_id = contrib.find(".//contrib-id[@contrib-id-type='orcid']")
            if contrib_id is not None:
                orcid = contrib_id.text

            # Get affiliations
            affiliations = []
            for xref in contrib.findall(".//xref[@ref-type='aff']"):
                rid = xref.get("rid", "")
                if rid in aff_map:
                    affiliations.append(aff_map[rid])

            authors.append(Author(
                given_names=given_names,
                surname=surname,
                email=email,
                affiliations=affiliations,
                orcid=orcid,
            ))

        return authors

    def _extract_journal(self, front: etree._Element) -> str | None:
        """Extract journal name."""
        journal_meta = front.find(".//journal-meta")
        if journal_meta is not None:
            journal_title = journal_meta.find(".//journal-title")
            if journal_title is not None:
                return self._get_text_content(journal_title)
        return None

    def _extract_publication_date(self, article_meta: etree._Element) -> date | None:
        """Extract publication date."""
        # Try epub date first, then other types
        for date_type in ["epub", "ppub", "collection", None]:
            if date_type:
                pub_date = article_meta.find(f".//pub-date[@pub-type='{date_type}']")
            else:
                pub_date = article_meta.find(".//pub-date")

            if pub_date is not None:
                try:
                    year = int(pub_date.findtext("year", "0"))
                    month = int(pub_date.findtext("month", "1"))
                    day = int(pub_date.findtext("day", "1"))
                    if year > 0:
                        return date(year, month, day)
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_id(self, article_meta: etree._Element, id_type: str) -> str | None:
        """Extract article identifier by type."""
        for article_id in article_meta.findall(".//article-id"):
            if article_id.get("pub-id-type") == id_type:
                return article_id.text
        return None

    def _extract_mesh_terms(self, article_meta: etree._Element) -> list[str]:
        """Extract MeSH terms."""
        mesh_terms = []
        for kwd_group in article_meta.findall(".//kwd-group"):
            if kwd_group.get("kwd-group-type") == "MeSH":
                for kwd in kwd_group.findall(".//kwd"):
                    term = self._get_text_content(kwd)
                    if term:
                        mesh_terms.append(term)
        return mesh_terms

    def _extract_keywords(self, article_meta: etree._Element) -> list[str]:
        """Extract keywords."""
        keywords = []
        for kwd_group in article_meta.findall(".//kwd-group"):
            # Skip MeSH terms (handled separately)
            if kwd_group.get("kwd-group-type") == "MeSH":
                continue
            for kwd in kwd_group.findall(".//kwd"):
                term = self._get_text_content(kwd)
                if term:
                    keywords.append(term)
        return keywords

    def _extract_article_type(self, article: etree._Element) -> str | None:
        """Extract article type."""
        return article.get("article-type")

    def _extract_sections(self, body: etree._Element) -> list[Section]:
        """Extract body sections recursively."""
        sections = []

        for sec in body.findall("./sec"):
            section = self._parse_section(sec)
            if section:
                sections.append(section)

        # If no sections found, treat entire body as one section
        if not sections:
            content = self._get_text_content(body)
            if content.strip():
                sections.append(Section(
                    title="Main Text",
                    content=content,
                    section_type="body",
                ))

        return sections

    def _parse_section(self, sec: etree._Element) -> Section | None:
        """Parse a single section element."""
        title_elem = sec.find("./title")
        title = self._get_text_content(title_elem) if title_elem is not None else "Untitled Section"

        # Get section type from title
        section_type = self._get_section_type(title)

        # Get direct paragraph content
        paragraphs = []
        for p in sec.findall("./p"):
            text = self._get_text_content(p)
            if text.strip():
                paragraphs.append(text)

        content = "\n\n".join(paragraphs)

        # Get subsections
        subsections = []
        for subsec in sec.findall("./sec"):
            sub = self._parse_section(subsec)
            if sub:
                subsections.append(sub)

        # Skip empty sections
        if not content.strip() and not subsections:
            return None

        return Section(
            title=title,
            content=content,
            section_type=section_type,
            subsections=subsections,
        )

    def _get_section_type(self, title: str) -> str | None:
        """Map section title to standardized section type."""
        title_lower = title.lower().strip()

        for pattern, section_type in self.SECTION_TYPE_MAP.items():
            if pattern in title_lower:
                return section_type

        return None

    def _extract_references(self, back: etree._Element) -> list[dict[str, Any]]:
        """Extract references."""
        references = []
        ref_list = back.find(".//ref-list")

        if ref_list is None:
            return references

        for ref in ref_list.findall(".//ref"):
            ref_data: dict[str, Any] = {
                "id": ref.get("id"),
            }

            # Try different citation formats
            citation = ref.find(".//mixed-citation") or ref.find(".//element-citation")
            if citation is not None:
                ref_data["type"] = citation.get("publication-type")
                ref_data["title"] = citation.findtext(".//article-title")
                ref_data["source"] = citation.findtext(".//source")
                ref_data["year"] = citation.findtext(".//year")
                ref_data["volume"] = citation.findtext(".//volume")
                ref_data["fpage"] = citation.findtext(".//fpage")
                ref_data["lpage"] = citation.findtext(".//lpage")

                # Get DOI if available
                pub_id = citation.find(".//pub-id[@pub-id-type='doi']")
                if pub_id is not None:
                    ref_data["doi"] = pub_id.text

            references.append(ref_data)

        return references

    def _get_text_content(self, elem: etree._Element | None) -> str:
        """Get all text content from an element, including nested elements."""
        if elem is None:
            return ""

        # Use itertext to get all text including from child elements
        return " ".join(elem.itertext()).strip()

    def _build_full_text(
        self,
        title: str,
        abstract: str | None,
        sections: list[Section],
    ) -> str:
        """Build concatenated full text from all parts."""
        parts = [title]

        if abstract:
            parts.append(abstract)

        def add_section_text(sec: Section, depth: int = 0) -> None:
            if sec.title:
                parts.append(sec.title)
            if sec.content:
                parts.append(sec.content)
            for subsec in sec.subsections:
                add_section_text(subsec, depth + 1)

        for section in sections:
            add_section_text(section)

        return "\n\n".join(parts)
