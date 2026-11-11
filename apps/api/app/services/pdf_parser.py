import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

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
                logger.warning(
                    f"[PDFParser] PyMuPDF parsing encountered an exception ({type(e).__name__}: {e}). "
                    f"Falling back safely to standard pypdf extraction for document '{document_id}'."
                )
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
            try:
                page = doc[page_idx]
                rect = page.rect
                page_width = float(rect.width)
                page_height = float(rect.height)

                # Check for images on page safely
                try:
                    images = page.get_images()
                    has_images = len(images) > 0
                except Exception:
                    has_images = False

                # Get text layout blocks: (x0, y0, x1, y1, text, block_no, block_type)
                # block_type 0 = text, 1 = image
                try:
                    blocks = page.get_text("blocks")
                except Exception as block_err:
                    logger.warning(f"[PDFParser] page.get_text('blocks') failed on page {page_num}: {block_err}. Trying simple text.")
                    raw_text = page.get_text() or ""
                    blocks = [(0, 0, page_width, page_height, raw_text, 0, 0)] if raw_text.strip() else []

                page_text_len = 0
                has_tables = False
            except Exception as page_load_err:
                logger.warning(f"[PDFParser] Error reading page {page_num}: {page_load_err}. Skipping page decomposition.")
                continue

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


    def extract_document_tree_and_hierarchy(
        self, file_path: str, document_id: str, filename: str
    ) -> Dict[str, Any]:
        """
        Extracts sections, headings, and subheadings into a hierarchical structure (L0-L3),
        generating graph nodes/links, hierarchy items, and evidence payloads.
        Prefers PyMuPDF TOC; falls back to layout blocks or pypdf.
        """
        cluster_palette = [
            "cluster_foundation",
            "cluster_ingestion",
            "cluster_retrieval",
            "cluster_evaluation",
            "cluster_security",
        ]

        title = filename.rsplit(".", 1)[0]
        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []
        hierarchy: List[Dict[str, Any]] = []
        evidence: List[Dict[str, Any]] = []

        # L0 Root Node
        root_node_id = f"node_root_{document_id[:8]}"
        nodes.append({
            "id": root_node_id,
            "label": title,
            "level": 0,
            "topic_cluster": "cluster_foundation",
            "panel_payload": f"Document: {filename}\nID: {document_id}\nRoot synthesis and conceptual anchor.",
        })
        hierarchy.append({
            "id": root_node_id,
            "title": title,
            "level": 0,
            "level_name": "L0 - Document Root",
            "page": 1,
            "parent_id": None,
        })

        if not os.path.exists(file_path):
            return {
                "document_id": document_id,
                "filename": filename,
                "graph": {"nodes": nodes, "links": links},
                "hierarchy": hierarchy,
                "evidence": evidence,
            }

        # Attempt fitz extraction
        toc = []
        total_pages = 1
        page_texts: Dict[int, str] = {}
        sample_blocks: List[Dict[str, Any]] = []

        if fitz is not None:
            try:
                doc = fitz.open(file_path)
                total_pages = len(doc)
                try:
                    toc = doc.get_toc() or []
                except Exception as toc_err:
                    logger.warning(f"[PDFParser] Failed to extract TOC outline: {toc_err}. Falling back to block layout analysis.")
                    toc = []

                # Extract first snippet of each page for evidence / payload safely
                for p_idx in range(min(total_pages, 50)):
                    p_num = p_idx + 1
                    try:
                        page = doc[p_idx]
                        try:
                            p_text = page.get_text() or ""
                        except Exception:
                            p_text = ""
                        page_texts[p_num] = p_text

                        try:
                            blocks = page.get_text("blocks")
                        except Exception:
                            blocks = []

                        for b in blocks:
                            if len(b) >= 5 and b[4].strip():
                                text_clean = b[4].strip()
                                if len(text_clean) < 120 and len(text_clean) > 3:
                                    sample_blocks.append({
                                        "page": p_num,
                                        "text": text_clean,
                                        "bbox": {"x0": b[0], "y0": b[1], "x1": b[2], "y1": b[3]},
                                    })
                    except Exception as page_err:
                        logger.warning(f"[PDFParser] Error reading page {p_num} for hierarchy: {page_err}")
                        continue

                doc.close()
            except Exception as e:
                logger.warning(f"[PDFParser] fitz error extracting hierarchy: {e}. Gracefully continuing with fallback.")

        # Branch 1: Rich TOC available from PDF outline
        if toc:
            # Map outline level (1, 2, 3) to (L1, L2, L3)
            # Level 1 -> H1, Level 2 -> H2, Level 3 -> L3 Concept
            parent_by_level: Dict[int, str] = {0: root_node_id}
            sec_idx = 0

            # Cap at 45 outline entries to keep graph performant and ultra-responsive
            step = 1
            if len(toc) > 45:
                # Prioritize level 1 and 2 entries
                filtered_toc = [t for t in toc if t[0] in [1, 2]]
                if len(filtered_toc) < 15:
                    filtered_toc = toc[:45]
                toc = filtered_toc[:45]

            for entry in toc:
                sec_idx += 1
                toc_level = entry[0]  # 1-indexed in PyMuPDF
                sec_title = entry[1].strip()
                page_target = entry[2] if len(entry) > 2 and isinstance(entry[2], int) else 1

                # Normalize level to 1, 2, or 3
                level = min(max(toc_level, 1), 3)
                node_id = f"sec_{document_id[:8]}_{sec_idx}"

                # Topic cluster round-robin
                cluster = cluster_palette[sec_idx % len(cluster_palette)]

                # Extract brief snippet for evidence payload
                snippet = page_texts.get(page_target, "")[:350].strip() or f"Section {sec_title} from page {page_target}."
                panel_payload = f"Section: {sec_title}\nLevel: L{level}\nPage: {page_target}\n\nEvidence Summary:\n{snippet}"

                nodes.append({
                    "id": node_id,
                    "label": sec_title[:65],
                    "level": level,
                    "topic_cluster": cluster,
                    "panel_payload": panel_payload,
                })

                # Determine parent
                parent_id = parent_by_level.get(level - 1, root_node_id)
                parent_by_level[level] = node_id

                links.append({
                    "source": parent_id,
                    "target": node_id,
                    "relationship": "contains",
                })

                hierarchy.append({
                    "id": node_id,
                    "title": sec_title,
                    "level": level,
                    "level_name": f"L{level} - {'Section' if level == 1 else 'Subsection' if level == 2 else 'Concept'}",
                    "page": page_target,
                    "parent_id": parent_id,
                })

                evidence.append({
                    "id": f"ev_{sec_idx}",
                    "section": sec_title,
                    "page": page_target,
                    "text": snippet[:200],
                    "level": level,
                })

        # Branch 2: No embedded TOC outline - extract from heading regex & layout blocks
        else:
            extracted_sections = []
            seen_headers = set()
            h_idx = 0

            # Scan sample blocks for candidate headings
            for b in sample_blocks:
                cand = b["text"].splitlines()[0].strip()
                cand_lower = cand.lower().rstrip(":")

                is_h = False
                lvl = 1

                if any(cand_lower == s or cand_lower.startswith(s + " ") or cand_lower.endswith(" " + s) for s in STANDARD_SECTIONS):
                    is_h = True
                    lvl = 1
                elif re.match(r'^(?:task\s+\d+|chapter\s+\d+|\d+\.\d+|\d+\s+[A-Z])', cand, re.IGNORECASE):
                    is_h = True
                    lvl = 1 if not re.match(r'^\d+\.\d+', cand) else 2
                elif cand.isupper() and len(cand) > 4 and len(cand) < 60:
                    is_h = True
                    lvl = 1
                elif len(cand) < 60 and HEADER_REGEX.match(cand):
                    is_h = True
                    lvl = 2

                if is_h and cand_lower not in seen_headers:
                    seen_headers.add(cand_lower)
                    h_idx += 1
                    extracted_sections.append({
                        "id": f"h_{document_id[:8]}_{h_idx}",
                        "title": cand,
                        "level": lvl,
                        "page": b["page"],
                    })
                    if len(extracted_sections) >= 35:
                        break

            # If still few headings, procedural section generator across pages
            if len(extracted_sections) < 3:
                for p_num in range(1, min(total_pages + 1, 8)):
                    h_idx += 1
                    extracted_sections.append({
                        "id": f"h_{document_id[:8]}_{h_idx}",
                        "title": f"Section {h_idx}: Page {p_num} Analysis",
                        "level": 1 if h_idx % 3 != 0 else 2,
                        "page": p_num,
                    })

            # Build nodes and links from extracted_sections
            last_l1_id = root_node_id
            for s in extracted_sections:
                lvl = s["level"]
                node_id = s["id"]
                cluster = cluster_palette[len(nodes) % len(cluster_palette)]
                p_text = page_texts.get(s["page"], "")[:350].strip()
                payload = f"Heading: {s['title']}\nLevel: L{lvl}\nPage: {s['page']}\n\nEvidence Summary:\n{p_text or 'Extracted document section.'}"

                nodes.append({
                    "id": node_id,
                    "label": s["title"][:65],
                    "level": lvl,
                    "topic_cluster": cluster,
                    "panel_payload": payload,
                })

                parent = last_l1_id if lvl > 1 else root_node_id
                if lvl == 1:
                    last_l1_id = node_id

                links.append({
                    "source": parent,
                    "target": node_id,
                    "relationship": "subdivision",
                })

                hierarchy.append({
                    "id": node_id,
                    "title": s["title"],
                    "level": lvl,
                    "level_name": f"L{lvl} - {'Section' if lvl == 1 else 'Subsection'}",
                    "page": s["page"],
                    "parent_id": parent,
                })

                evidence.append({
                    "id": f"ev_{s['id']}",
                    "section": s["title"],
                    "page": s["page"],
                    "text": p_text[:200] if p_text else s["title"],
                    "level": lvl,
                })

        return {
            "document_id": document_id,
            "filename": filename,
            "graph": {
                "nodes": nodes,
                "links": links,
            },
            "hierarchy": hierarchy,
            "evidence": evidence,
        }


pdf_parser_service = PDFParserService()
