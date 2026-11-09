import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class SemanticChunkData:
    chunk_id: str
    document_id: str
    page_number: int
    section_title: str
    subsection: Optional[str]
    context_header: str
    content_text: str
    embedded_text: str
    token_count: int
    chunk_index: int


class SectionAwareChunker:
    """
    Section-aware semantic chunker for academic literature.
    Preserves structural context, natural sentence boundaries, and page provenance.
    Avoids naive fixed character splitting that severs math formulas, tables, and citations.
    """

    def __init__(self, target_tokens: int = 800, overlap_tokens: int = 150):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens

    def estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation: ~0.75 words per token (1 word ≈ 1.33 tokens)."""
        words = len(text.split())
        return int(words * 1.33)

    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences cleanly along punctuation and double-newlines."""
        # Normalize double newlines
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        sentences = []
        for p in paragraphs:
            # Match sentence endings (.!?) followed by space and capital letter or end of string
            raw_sents = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])', p)
            for s in raw_sents:
                clean = s.strip()
                if clean:
                    sentences.append(clean)
        return sentences

    def chunk_extracted_nodes(
        self,
        document_id: str,
        document_title: str,
        extracted_contents: List[Any],  # list of ExtractedContent or dicts
    ) -> List[SemanticChunkData]:
        """
        Converts extracted document units into section-aware, overlapping semantic chunks.
        """
        if not extracted_contents:
            return []

        # 1. Group content nodes by (page_number, section, subsection)
        grouped_units = []
        current_group: Dict[str, Any] = {
            "page_number": getattr(extracted_contents[0], "page_number", 1),
            "section": getattr(extracted_contents[0], "section", "General"),
            "subsection": getattr(extracted_contents[0], "subsection", None),
            "texts": [],
        }

        for node in extracted_contents:
            p_num = getattr(node, "page_number", 1)
            sec = getattr(node, "section", "General") or "General"
            subsec = getattr(node, "subsection", None)
            text = getattr(node, "source_text", "").strip()

            if not text:
                continue

            # If section or page changes, start a new group
            if (
                p_num != current_group["page_number"]
                or sec != current_group["section"]
                or subsec != current_group["subsection"]
            ):
                if current_group["texts"]:
                    grouped_units.append(current_group)
                current_group = {
                    "page_number": p_num,
                    "section": sec,
                    "subsection": subsec,
                    "texts": [text],
                }
            else:
                current_group["texts"].append(text)

        if current_group["texts"]:
            grouped_units.append(current_group)

        # 2. Build overlapping chunks respecting section boundaries
        chunks: List[SemanticChunkData] = []
        chunk_idx = 0

        for group in grouped_units:
            p_num = group["page_number"]
            sec = group["section"]
            subsec = group["subsection"]

            # Construct context breadcrumb header
            if subsec:
                header = f"[Document: {document_title}] [Section: {sec} > {subsec}]"
            else:
                header = f"[Document: {document_title}] [Section: {sec}]"

            # Combine texts in group into paragraph/sentence stream
            full_group_text = "\n\n".join(group["texts"])
            sentences = self.split_into_sentences(full_group_text)

            if not sentences:
                continue

            # Sliding window over sentences
            curr_chunk_sents: List[str] = []
            curr_tokens = 0

            for sent in sentences:
                sent_tokens = self.estimate_tokens(sent)

                # If single sentence exceeds target, add it directly as a standalone chunk
                if sent_tokens >= self.target_tokens:
                    if curr_chunk_sents:
                        chunk_idx += 1
                        c_text = " ".join(curr_chunk_sents)
                        embedded = f"{header}\n{c_text}"
                        chunks.append(
                            SemanticChunkData(
                                chunk_id=f"chk_{document_id}_p{p_num}_{chunk_idx}",
                                document_id=document_id,
                                page_number=p_num,
                                section_title=sec,
                                subsection=subsec,
                                context_header=header,
                                content_text=c_text,
                                embedded_text=embedded,
                                token_count=curr_tokens,
                                chunk_index=chunk_idx,
                            )
                        )
                        curr_chunk_sents = []
                        curr_tokens = 0

                    chunk_idx += 1
                    embedded = f"{header}\n{sent}"
                    chunks.append(
                        SemanticChunkData(
                            chunk_id=f"chk_{document_id}_p{p_num}_{chunk_idx}",
                            document_id=document_id,
                            page_number=p_num,
                            section_title=sec,
                            subsection=subsec,
                            context_header=header,
                            content_text=sent,
                            embedded_text=embedded,
                            token_count=sent_tokens,
                            chunk_index=chunk_idx,
                        )
                    )
                    continue

                if curr_tokens + sent_tokens > self.target_tokens and curr_chunk_sents:
                    # Flush current window
                    chunk_idx += 1
                    c_text = " ".join(curr_chunk_sents)
                    embedded = f"{header}\n{c_text}"
                    chunks.append(
                        SemanticChunkData(
                            chunk_id=f"chk_{document_id}_p{p_num}_{chunk_idx}",
                            document_id=document_id,
                            page_number=p_num,
                            section_title=sec,
                            subsection=subsec,
                            context_header=header,
                            content_text=c_text,
                            embedded_text=embedded,
                            token_count=curr_tokens,
                            chunk_index=chunk_idx,
                        )
                    )

                    # Compute overlap from trailing sentences
                    overlap_sents: List[str] = []
                    overlap_tokens = 0
                    for s in reversed(curr_chunk_sents):
                        s_tok = self.estimate_tokens(s)
                        if overlap_tokens + s_tok <= self.overlap_tokens:
                            overlap_sents.insert(0, s)
                            overlap_tokens += s_tok
                        else:
                            break

                    curr_chunk_sents = overlap_sents + [sent]
                    curr_tokens = overlap_tokens + sent_tokens
                else:
                    curr_chunk_sents.append(sent)
                    curr_tokens += sent_tokens

            # Flush remaining sentences in group
            if curr_chunk_sents:
                chunk_idx += 1
                c_text = " ".join(curr_chunk_sents)
                embedded = f"{header}\n{c_text}"
                chunks.append(
                    SemanticChunkData(
                        chunk_id=f"chk_{document_id}_p{p_num}_{chunk_idx}",
                        document_id=document_id,
                        page_number=p_num,
                        section_title=sec,
                        subsection=subsec,
                        context_header=header,
                        content_text=c_text,
                        embedded_text=embedded,
                        token_count=curr_tokens,
                        chunk_index=chunk_idx,
                    )
                )

        return chunks


semantic_chunker = SectionAwareChunker(target_tokens=800, overlap_tokens=150)
