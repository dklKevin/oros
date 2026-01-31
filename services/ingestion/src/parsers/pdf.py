"""
PDF Parser for biomedical documents.

Parses PDF files and extracts structured content including:
- Title, abstract, full text sections
- Authors (from metadata and text)
- DOI and other identifiers
- References
"""

import re
from datetime import date
from typing import Any

import fitz  # PyMuPDF

from services.shared.logging import get_logger
from services.ingestion.src.parsers.base import (
    Author,
    BaseParser,
    ParsedDocument,
    ParseError,
    Section,
)

logger = get_logger(__name__)


class PDFParser(BaseParser):
    """Parser for PDF documents, optimized for biomedical papers."""

    # Common section titles in biomedical papers
    SECTION_PATTERNS = {
        "abstract": r"^abstract\s*$",
        "introduction": r"^(introduction|background)\s*$",
        "methods": r"^(methods?|materials?\s*(and|&)\s*methods?|experimental)\s*$",
        "results": r"^(results?|findings?)\s*$",
        "discussion": r"^discussion\s*$",
        "conclusion": r"^(conclusions?|summary)\s*$",
        "references": r"^(references?|bibliography|literature\s*cited)\s*$",
        "acknowledgments": r"^(acknowledgm?ents?)\s*$",
        "supplementary": r"^(supplementary|supporting)\s*(materials?|information)?\s*$",
    }

    # DOI pattern
    DOI_PATTERN = re.compile(
        r"(?:doi[:\s]*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,}/[^\s]+)",
        re.IGNORECASE,
    )

    # PMID pattern
    PMID_PATTERN = re.compile(r"PMID[:\s]*(\d{7,8})", re.IGNORECASE)

    # PMC ID pattern
    PMCID_PATTERN = re.compile(r"PMC\s*ID?[:\s]*(PMC\d+)|(?:^|\s)(PMC\d+)", re.IGNORECASE)

    def can_parse(self, content: bytes, filename: str | None = None) -> bool:
        """
        Check if content is a PDF file.

        Args:
            content: Raw file content as bytes
            filename: Optional filename for format detection

        Returns:
            True if this parser can handle the content
        """
        # Check magic bytes for PDF
        if content.startswith(b"%PDF"):
            return True

        # Check filename extension as fallback
        if filename and filename.lower().endswith(".pdf"):
            return True

        return False

    def parse(self, content: bytes) -> ParsedDocument:
        """
        Parse PDF content into a structured document.

        Args:
            content: Raw PDF content as bytes

        Returns:
            ParsedDocument with extracted content

        Raises:
            ParseError: If PDF cannot be parsed
        """
        if not content:
            raise ParseError("Empty content provided")

        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            logger.error("pdf_open_error", error=str(e))
            raise ParseError(f"Failed to open PDF: {e}", {"error": str(e)})

        try:
            if doc.page_count == 0:
                raise ParseError("PDF has no pages")

            # Extract metadata
            metadata = doc.metadata or {}

            # Extract full text and analyze structure
            pages_text = self._extract_pages_text(doc)
            full_text = "\n\n".join(pages_text)

            if not full_text.strip():
                raise ParseError("PDF contains no extractable text")

            # Extract structured content
            title = self._extract_title(doc, metadata, full_text)
            abstract = self._extract_abstract(full_text)
            sections = self._extract_sections(full_text)
            authors = self._extract_authors(doc, metadata, full_text)
            references = self._extract_references(full_text)

            # Extract identifiers
            doi = self._extract_doi(full_text)
            pmcid = self._extract_pmcid(full_text)
            pmid = self._extract_pmid(full_text)

            # Extract keywords
            keywords = self._extract_keywords(metadata)

            # Extract publication date from metadata
            pub_date = self._extract_publication_date(metadata)

            return ParsedDocument(
                title=title,
                abstract=abstract,
                sections=sections,
                full_text=full_text,
                authors=authors,
                journal=None,  # Hard to extract from PDF
                publication_date=pub_date,
                doi=doi,
                pmcid=pmcid,
                pmid=pmid,
                mesh_terms=[],  # Not typically in PDF
                keywords=keywords,
                article_type=None,
                references=references,
                raw_metadata={
                    "parser": "pdf",
                    "version": "1.0",
                    "page_count": doc.page_count,
                    "pdf_metadata": metadata,
                },
            )

        except ParseError:
            raise
        except Exception as e:
            logger.error("pdf_parse_error", error=str(e))
            raise ParseError(f"Failed to parse PDF: {e}")
        finally:
            doc.close()

    def _extract_pages_text(self, doc: fitz.Document) -> list[str]:
        """Extract text from all pages."""
        pages_text = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages_text.append(text.strip())
        return pages_text

    def _extract_title(
        self,
        doc: fitz.Document,
        metadata: dict[str, Any],
        full_text: str,
    ) -> str:
        """Extract document title from metadata or first page content."""
        # Try metadata first
        if metadata.get("title"):
            return metadata["title"].strip()

        # Try to find title from first page
        # Typically the title is in larger font at the top
        if doc.page_count > 0:
            first_page = doc[0]
            blocks = first_page.get_text("dict")["blocks"]

            # Look for text blocks with larger font size
            title_candidates = []
            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            size = span.get("size", 12)
                            # Title typically has larger font (>14pt)
                            if text and size > 14 and len(text) > 10:
                                title_candidates.append((size, text))

            if title_candidates:
                # Sort by font size (descending) and take the largest
                title_candidates.sort(key=lambda x: x[0], reverse=True)
                return title_candidates[0][1]

        # Fallback: first non-empty line
        lines = full_text.split("\n")
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not line.startswith(("http", "doi", "DOI")):
                return line

        return "Untitled Document"

    def _extract_abstract(self, full_text: str) -> str | None:
        """Extract abstract from document text."""
        # Look for "Abstract" section
        lines = full_text.split("\n")
        abstract_lines = []
        in_abstract = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Start of abstract
            if re.match(r"^abstract\s*:?\s*$", line_lower):
                in_abstract = True
                continue

            # End of abstract (next section header)
            if in_abstract:
                # Check for common section headers that end abstract
                if re.match(
                    r"^(introduction|background|keywords?|methods?|1\.?\s*introduction)\s*:?\s*$",
                    line_lower,
                ):
                    break

                # Collect abstract content
                if line_stripped:
                    abstract_lines.append(line_stripped)
                # Don't include too many empty lines
                elif abstract_lines and not abstract_lines[-1] == "":
                    abstract_lines.append("")

                # Limit abstract length
                if len(abstract_lines) > 30:
                    break

        if abstract_lines:
            # Clean up trailing empty strings
            while abstract_lines and abstract_lines[-1] == "":
                abstract_lines.pop()
            return " ".join(abstract_lines)

        return None

    def _extract_sections(self, full_text: str) -> list[Section]:
        """Extract named sections from document text."""
        sections = []
        lines = full_text.split("\n")

        current_section: dict[str, Any] | None = None

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Check if this line is a section header
            section_type = self._get_section_type(line_lower)

            if section_type and len(line_stripped) < 100:  # Headers are typically short
                # Save previous section
                if current_section and current_section["content"]:
                    sections.append(
                        Section(
                            title=current_section["title"],
                            content="\n".join(current_section["content"]).strip(),
                            section_type=current_section["type"],
                        )
                    )

                # Start new section
                current_section = {
                    "title": line_stripped,
                    "type": section_type,
                    "content": [],
                }
            elif current_section is not None:
                # Add content to current section
                if line_stripped:
                    current_section["content"].append(line_stripped)

        # Don't forget the last section
        if current_section and current_section["content"]:
            sections.append(
                Section(
                    title=current_section["title"],
                    content="\n".join(current_section["content"]).strip(),
                    section_type=current_section["type"],
                )
            )

        return sections

    def _get_section_type(self, title_lower: str) -> str | None:
        """Map section title to standardized section type."""
        for section_type, pattern in self.SECTION_PATTERNS.items():
            if re.match(pattern, title_lower, re.IGNORECASE):
                return section_type
        return None

    def _extract_authors(
        self,
        doc: fitz.Document,
        metadata: dict[str, Any],
        full_text: str,
    ) -> list[Author]:
        """Extract author information from metadata and text."""
        authors = []

        # Try metadata first
        author_str = metadata.get("author", "")
        if author_str:
            # Split by common separators
            for sep in [";", ",", " and ", "&"]:
                if sep in author_str:
                    author_names = author_str.split(sep)
                    break
            else:
                author_names = [author_str]

            for name in author_names:
                name = name.strip()
                if not name:
                    continue

                # Parse name into parts
                parts = name.split()
                if len(parts) >= 2:
                    surname = parts[-1]
                    given_names = " ".join(parts[:-1])
                else:
                    surname = name
                    given_names = ""

                authors.append(
                    Author(
                        given_names=given_names,
                        surname=surname,
                    )
                )

        # If no authors from metadata, try to parse from text
        if not authors:
            authors = self._extract_authors_from_text(full_text)

        return authors

    def _extract_authors_from_text(self, full_text: str) -> list[Author]:
        """Extract authors from document text (typically near the title)."""
        authors = []

        # Get first ~2000 chars where authors are likely to appear
        header_text = full_text[:2000]
        lines = header_text.split("\n")

        # Look for lines that look like author names
        # (appear after title, before abstract, contain names with possible affiliations)
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()

            # Skip obvious non-author lines
            if not line or len(line) < 5:
                continue
            if re.match(r"^(abstract|introduction|keywords?|doi|http)", line.lower()):
                continue
            if line.lower().startswith(("received", "accepted", "published")):
                continue

            # Look for patterns like "John Smith¹, Jane Doe²*" or "J. Smith, J. Doe"
            author_pattern = r"^([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)(?:\s*[¹²³⁴⁵⁶⁷⁸⁹⁰*,]+)?\s*(?:,|and|&|$)"
            if re.search(author_pattern, line):
                # This looks like an author line
                # Extract individual names
                # Remove affiliation markers and split
                clean_line = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§]", "", line)
                name_parts = re.split(r"\s*[,;&]\s*|\s+and\s+", clean_line)

                for name in name_parts:
                    name = name.strip()
                    if not name or len(name) < 3:
                        continue

                    parts = name.split()
                    if len(parts) >= 2:
                        # Check if looks like a name (not institution)
                        if not any(
                            kw in name.lower()
                            for kw in ["university", "institute", "department", "hospital"]
                        ):
                            authors.append(
                                Author(
                                    given_names=" ".join(parts[:-1]),
                                    surname=parts[-1],
                                )
                            )

                if authors:
                    break  # Found authors, stop looking

        return authors

    def _extract_references(self, full_text: str) -> list[dict[str, Any]]:
        """Extract references from document text."""
        references = []

        # Find references section
        ref_start = None
        lines = full_text.split("\n")

        for i, line in enumerate(lines):
            if re.match(r"^(references?|bibliography|literature\s*cited)\s*$", line.strip().lower()):
                ref_start = i + 1
                break

        if ref_start is None:
            return references

        # Extract reference entries
        ref_text = "\n".join(lines[ref_start:])

        # Common reference patterns: [1], 1., (1)
        ref_pattern = r"(?:^|\n)\s*(?:\[?\d+\]?\.?|\(\d+\))\s+(.+?)(?=\n\s*(?:\[?\d+\]?\.?|\(\d+\))\s+|\Z)"

        matches = re.findall(ref_pattern, ref_text, re.DOTALL)

        for i, match in enumerate(matches[:100], 1):  # Limit to 100 refs
            ref_text_clean = " ".join(match.split())  # Normalize whitespace

            ref_data: dict[str, Any] = {
                "id": str(i),
                "raw": ref_text_clean,
            }

            # Try to extract DOI from reference
            doi_match = self.DOI_PATTERN.search(ref_text_clean)
            if doi_match:
                ref_data["doi"] = doi_match.group(1)

            # Try to extract year
            year_match = re.search(r"\b(19|20)\d{2}\b", ref_text_clean)
            if year_match:
                ref_data["year"] = year_match.group(0)

            references.append(ref_data)

        return references

    def _extract_doi(self, full_text: str) -> str | None:
        """Extract DOI from document text."""
        # Look in first part of document where DOI typically appears
        header_text = full_text[:5000]

        match = self.DOI_PATTERN.search(header_text)
        if match:
            doi = match.group(1)
            # Clean up DOI
            doi = doi.rstrip(".,;)")
            return doi

        return None

    def _extract_pmcid(self, full_text: str) -> str | None:
        """Extract PMC ID from document text."""
        header_text = full_text[:5000]

        match = self.PMCID_PATTERN.search(header_text)
        if match:
            return match.group(1) or match.group(2)

        return None

    def _extract_pmid(self, full_text: str) -> str | None:
        """Extract PMID from document text."""
        header_text = full_text[:5000]

        match = self.PMID_PATTERN.search(header_text)
        if match:
            return match.group(1)

        return None

    def _extract_keywords(self, metadata: dict[str, Any]) -> list[str]:
        """Extract keywords from PDF metadata."""
        keywords_str = metadata.get("keywords", "")
        if not keywords_str:
            return []

        # Split by common separators
        keywords = re.split(r"[,;]", keywords_str)
        return [kw.strip() for kw in keywords if kw.strip()]

    def _extract_publication_date(self, metadata: dict[str, Any]) -> date | None:
        """Extract publication date from PDF metadata."""
        # Try creationDate or modDate
        for key in ["creationDate", "modDate"]:
            date_str = metadata.get(key, "")
            if date_str:
                try:
                    # PDF date format: D:YYYYMMDDHHmmSS
                    if date_str.startswith("D:"):
                        date_str = date_str[2:]
                    year = int(date_str[:4])
                    month = int(date_str[4:6]) if len(date_str) >= 6 else 1
                    day = int(date_str[6:8]) if len(date_str) >= 8 else 1
                    return date(year, month, day)
                except (ValueError, IndexError):
                    continue

        return None
