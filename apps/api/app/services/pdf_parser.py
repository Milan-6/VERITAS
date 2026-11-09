import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

import pypdf

DOI_REGEX = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b')
HEADER_REGEX = re.compile(
    r'^((?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9\s\-_,:]{2,80})$'
)
STANDARD_SECTIONS = [
    "abstract", "introduction", "related work", "background",
    "methodology", "method", "proposed method", "system architecture",
    "experiments", "experimental setup", "results", "discussion",
    "evaluation", "conclusion", "conclusions", "future work",
    "references", "bibliography", "acknowledgments", "appendix"
]
FIGURE_CAPTION_REGEX = re.compile(r'^(fig(ure)?\.?\s*\d+[:.\s]|table\s*\d+[:.\s])', re.IGNORECASE)
MATH_INDICATORS = ["\\begin{equation}", "$$", "\\alpha", "\\beta", "\\gamma", "\\sigma", "\\int", "\\sum", "∑", "∫", "∂", "√", "∈", "∀", "∃"]


@dataclass
class ParsedContentItem:
    chunk_id: str
    page_number: int
    content_type: str  # paragraph, header, table, figure_caption, math_expression, reference
    source_text: str
    section: str
    subsection: Optional[str]
    extraction_method: str
    bounding_box: Optional[Dict[str, float]]
    order_index: int


@dataclass
class ParsedSectionItem:
    section_title: str
    section_level: int
    start_page: int
    end_page: int
    order_index: int


@dataclass
class ParsedPageItem:
    page_number: int
    width: float
    height: float
    text_length: int
    has_images: bool
    has_tables: bool


@dataclass
class ParsedDocumentResult:
    title: str
    authors: List[str]
    abstract: Optional[str]
    keywords: List[str]
    publication_date: Optional[str]
    doi: Optional[str]
    journal_or_conference: Optional[str]
    total_pages: int
    raw_metadata: Dict[str, Any]
    pages: List[ParsedPageItem] = field(default_factory=list)
    sections: List[ParsedSectionItem] = field(default_factory=list)
    contents: List[ParsedContentItem] = field(default_factory=list)


class PDFParserService:
    def __init__(self):
        self.has_mupdf = fitz is not None

    def parse_pdf(self, file_path: str, document_id: str) -> ParsedDocumentResult:
        """
        Parses a PDF file using PyMuPDF with layout awareness,
        falling back to pypdf if PyMuPDF is unavailable or encounters an error.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        if self.has_mupdf:
            try:
                return self._parse_with_pymupdf(file_path, document_id)
            except Exception as e:
                # Log and fallback to pypdf
                return self._parse_with_pypdf(file_path, document_id, fallback_reason=str(e))
        else:
            return self._parse_with_pypdf(file_path, document_id)

    def _parse_with_pymupdf(self, file_path: str, document_id: str) -> ParsedDocumentResult:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        if total_pages == 0:
            raise ValueError("PDF document contains 0 pages.")

        raw_meta = dict(doc.metadata) if doc.metadata else {}
        doc_title = (raw_meta.get("title") or "").strip()
        doc_author = (raw_meta.get("author") or "").strip()
        doc_subject = (raw_meta.get("subject") or "").strip()
        doc_keywords = [k.strip() for k in (raw_meta.get("keywords") or "").split(";") if k.strip()]
        doc_pub_date = raw_meta.get("creationDate") or raw_meta.get("modDate")

        authors_list = [a.strip() for a in re.split(r'[,;]| and ', doc_author) if a.strip()] if doc_author else []

        full_extracted_text = ""
        found_doi = None
        extracted_pages: List[ParsedPageItem] = []
        extracted_sections: List[ParsedSectionItem] = []
        extracted_contents: List[ParsedContentItem] = []

        current_section = "Header / Front Matter"
        current_subsection: Optional[str] = None
        section_order = 0
        chunk_order = 0
        detected_sections_dict = {}

        abstract_text: Optional[str] = None
        collecting_abstract = False
        abstract_chunks = []

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]
            rect = page.rect
            page_width = float(rect.width)
            page_height = float(rect.height)

            # Check for images on page
            images = page.get_images()
            has_images = len(images) > 0

            # Get text layout blocks: (x0, y0, x1, y1, text, block_no, block_type)
            # block_type 0 = text, 1 = image
            blocks = page.get_text("blocks")
            page_text_len = 0
            has_tables = False

            for block in blocks:
                if len(block) < 5:
                    continue
                x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
                clean_text = text.strip()
                if not clean_text:
                    continue

                page_text_len += len(clean_text)
                full_extracted_text += clean_text + "\n"

                # Check DOI
                if not found_doi:
                    doi_match = DOI_REGEX.search(clean_text)
                    if doi_match:
                        found_doi = doi_match.group(1)

                bbox = {"x0": round(float(x0), 2), "y0": round(float(y0), 2), "x1": round(float(x1), 2), "y1": round(float(y1), 2)}

                # Break multi-paragraph blocks separated by double-newlines into atomic semantic units
                sub_units = [u.strip() for u in clean_text.split("\n\n") if u.strip()]
                if not sub_units:
                    sub_units = [clean_text]

                for unit_text in sub_units:
                    content_type = "paragraph"
                    lines = unit_text.splitlines()
                    first_line = lines[0].strip()

                    # 1. Header & Section Recognition
                    is_header = False
                    lower_first = first_line.lower().rstrip(":")

                    # Check standard section names or numbered headings (e.g., "1. Introduction", "2 Related Work")
                    if (lower_first in STANDARD_SECTIONS or 
                        any(lower_first == s or lower_first.startswith(s + " ") or lower_first.endswith(" " + s) for s in STANDARD_SECTIONS) or
                        (len(first_line) < 80 and HEADER_REGEX.match(first_line) and len(lines) <= 2)):
                        is_header = True
                        content_type = "header"

                        section_title = first_line
                        is_sub = bool(re.match(r'^\d+\.\d+', section_title))
                        if is_sub:
                            current_subsection = section_title
                            level = 2
                        else:
                            current_section = section_title
                            current_subsection = None
                            level = 1

                        if section_title.lower() not in detected_sections_dict:
                            section_order += 1
                            sec_item = ParsedSectionItem(
                                section_title=section_title,
                                section_level=level,
                                start_page=page_num,
                                end_page=page_num,
                                order_index=section_order
                            )
                            detected_sections_dict[section_title.lower()] = sec_item
                            extracted_sections.append(sec_item)
                        else:
                            detected_sections_dict[section_title.lower()].end_page = page_num

                        # Abstract detection
                        if "abstract" in lower_first:
                            collecting_abstract = True
                            if len(lines) > 1:
                                abstract_chunks.append("\n".join(lines[1:]))
                        elif collecting_abstract:
                            collecting_abstract = False

                    # 2. Figure / Table Caption
                    elif FIGURE_CAPTION_REGEX.match(first_line):
                        content_type = "figure_caption"
                        if "table" in first_line.lower():
                            has_tables = True
                            content_type = "table"

                    # 3. Math Expression Detection
                    elif any(math_ind in unit_text for math_ind in MATH_INDICATORS) or ("=" in unit_text and len(unit_text) < 120 and any(c in unit_text for c in "+-*/^_{}")):
                        content_type = "math_expression"

                    # 4. References / Bibliography entries
                    elif "reference" in current_section.lower() or "bibliography" in current_section.lower():
                        content_type = "reference"

                    # Title extraction: the first substantial text unit on Page 1 is the Title
                    if not doc_title and page_num == 1 and chunk_order <= 2:
                        first_clean = first_line.strip()
                        if not first_clean.lower().startswith(("doi:", "arxiv:", "issn:", "isbn:")) and len(first_clean) > 3:
                            doc_title = first_clean

                    if collecting_abstract and not is_header:
                        abstract_chunks.append(unit_text)

                    chunk_order += 1
                    chunk_id = f"doc_{document_id}_p{page_num}_c{chunk_order}"

                    extracted_contents.append(
                        ParsedContentItem(
                            chunk_id=chunk_id,
                            page_number=page_num,
                            content_type=content_type,
                            source_text=unit_text,
                            section=current_section,
                            subsection=current_subsection,
                            extraction_method="pymupdf_layout",
                            bounding_box=bbox,
                            order_index=chunk_order
                        )
                    )

            extracted_pages.append(
                ParsedPageItem(
                    page_number=page_num,
                    width=page_width,
                    height=page_height,
                    text_length=page_text_len,
                    has_images=has_images,
                    has_tables=has_tables
                )
            )

        doc.close()

        if abstract_chunks and not abstract_text:
            abstract_text = "\n\n".join(abstract_chunks).strip()

        # Extract Keywords from text if missing in metadata
        if not doc_keywords:
            kw_match = re.search(r'(?:keywords|index terms)[:\s]+(.*?)(?:\n\n|\.\s|\Z)', full_extracted_text, re.IGNORECASE)
            if kw_match:
                doc_keywords = [k.strip() for k in re.split(r'[,;•]', kw_match.group(1)) if k.strip()]

        return ParsedDocumentResult(
            title=doc_title or "Untitled Research Document",
            authors=authors_list,
            abstract=abstract_text,
            keywords=doc_keywords,
            publication_date=doc_pub_date,
            doi=found_doi,
            journal_or_conference=doc_subject or None,
            total_pages=total_pages,
            raw_metadata=raw_meta,
            pages=extracted_pages,
            sections=extracted_sections,
            contents=extracted_contents
        )

    def _parse_with_pypdf(self, file_path: str, document_id: str, fallback_reason: str = "") -> ParsedDocumentResult:
        """Fallback extraction when PyMuPDF is unavailable."""
        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDF document contains 0 pages.")

        meta = reader.metadata or {}
        raw_meta = {k: str(v) for k, v in meta.items()} if meta else {}
        if fallback_reason:
            raw_meta["fallback_reason"] = fallback_reason

        title = meta.title or "Untitled Research Document"
        author = meta.author or ""
        authors = [a.strip() for a in author.split(",") if a.strip()]

        extracted_pages: List[ParsedPageItem] = []
        extracted_sections: List[ParsedSectionItem] = [
            ParsedSectionItem(section_title="Document Body", section_level=1, start_page=1, end_page=total_pages, order_index=1)
        ]
        extracted_contents: List[ParsedContentItem] = []
        chunk_order = 0
        found_doi = None

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            text = page.extract_text() or ""
            text_len = len(text)
            
            if not found_doi:
                doi_match = DOI_REGEX.search(text)
                if doi_match:
                    found_doi = doi_match.group(1)

            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p in paragraphs:
                chunk_order += 1
                chunk_id = f"doc_{document_id}_p{page_num}_c{chunk_order}"
                extracted_contents.append(
                    ParsedContentItem(
                        chunk_id=chunk_id,
                        page_number=page_num,
                        content_type="paragraph",
                        source_text=p,
                        section="Document Body",
                        subsection=None,
                        extraction_method="pypdf_fallback",
                        bounding_box=None,
                        order_index=chunk_order
                    )
                )

            extracted_pages.append(
                ParsedPageItem(
                    page_number=page_num,
                    width=float(page.mediabox.width) if page.mediabox else 0.0,
                    height=float(page.mediabox.height) if page.mediabox else 0.0,
                    text_length=text_len,
                    has_images=len(page.images) > 0,
                    has_tables=False
                )
            )

        return ParsedDocumentResult(
            title=title,
            authors=authors,
            abstract=None,
            keywords=[],
            publication_date=str(meta.creation_date) if meta.creation_date else None,
            doi=found_doi,
            journal_or_conference=None,
            total_pages=total_pages,
            raw_metadata=raw_meta,
            pages=extracted_pages,
            sections=extracted_sections,
            contents=extracted_contents
        )


pdf_parser_service = PDFParserService()
