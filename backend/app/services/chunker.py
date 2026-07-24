import re
import tiktoken
from typing import List, Dict, Any

class SemanticChunkerService:
    def __init__(self, model_name: str = "cl100k_base"):
        try:
            self.encoder = tiktoken.get_encoding(model_name)
        except Exception:
            # Fallback encoder if offline
            self.encoder = None

    def count_tokens(self, text: str) -> int:
        if self.encoder:
            return len(self.encoder.encode(text))
        # Fallback heuristic: 1 token = 4 characters
        return len(text) // 4

    def chunk_document(
        self,
        pages: List[Dict[str, Any]],
        target_size: int = 800,
        overlap_size: int = 150
    ) -> List[Dict[str, Any]]:
        """
        Groups document pages into semantic, metadata-preserving chunks.
        """
        chunks = []
        
        # State tracking for sections
        current_chapter = None
        current_section = None
        current_subsection = None

        # Build list of paragraphs with page metadata
        paragraphs = []
        for p in pages:
            text = p["text"]
            page_idx = p["page_index"]
            printed_page = p["printed_page"]
            
            # Simple paragraph split
            raw_paras = text.split("\n\n")
            for para in raw_paras:
                para = para.strip()
                if not para:
                    continue
                
                # Check for structural headings to track section hierarchy
                # E.g. "Chapter 4 Database Normalization"
                chap_match = re.match(r'^chapter\s+(\d+|[ivxldc]+)[:\-\s]+(.*)', para, re.IGNORECASE)
                sec_match = re.match(r'^(\d+\.\d+)\s+(.*)', para)
                subsec_match = re.match(r'^(\d+\.\d+\.\d+)\s+(.*)', para)

                if chap_match:
                    current_chapter = f"Chapter {chap_match.group(1)}: {chap_match.group(2)[:60]}"
                    current_section = None
                    current_subsection = None
                elif subsec_match:
                    current_subsection = f"Subsection {subsec_match.group(1)}: {subsec_match.group(2)[:60]}"
                elif sec_match:
                    current_section = f"Section {sec_match.group(1)}: {sec_match.group(2)[:60]}"
                    current_subsection = None

                paragraphs.append({
                    "text": para,
                    "pdf_page": page_idx,
                    "printed_page": printed_page,
                    "chapter": current_chapter,
                    "section": current_section,
                    "subsection": current_subsection
                })

        # Assemble paragraphs into overlapping chunks
        current_chunk_paras = []
        current_chunk_tokens = 0

        for idx, para in enumerate(paragraphs):
            para_tokens = self.count_tokens(para["text"])
            
            # If a single paragraph is extremely large, split it by sentences or characters
            if para_tokens > target_size:
                # Flush existing chunk buffer if any
                if current_chunk_paras:
                    chunks.append(self._build_chunk(current_chunk_paras, current_chunk_tokens))
                    current_chunk_paras = []
                    current_chunk_tokens = 0
                
                # Split large paragraph into sentences
                sentences = re.split(r'(?<=[.!?])\s+', para["text"])
                sub_paras = []
                sub_tokens = 0
                for sent in sentences:
                    sent_tokens = self.count_tokens(sent)
                    if sub_tokens + sent_tokens > target_size:
                        chunks.append(self._build_chunk([{
                            **para, "text": " ".join(sub_paras)
                        }], sub_tokens))
                        # Retain overlap sentences
                        overlap_sents = sub_paras[-3:] if len(sub_paras) > 3 else sub_paras
                        sub_paras = list(overlap_sents)
                        sub_tokens = self.count_tokens(" ".join(sub_paras))
                    sub_paras.append(sent)
                    sub_tokens += sent_tokens
                
                if sub_paras:
                    chunks.append(self._build_chunk([{
                        **para, "text": " ".join(sub_paras)
                    }], sub_tokens))
                continue

            if current_chunk_tokens + para_tokens > target_size:
                # Emit current chunk
                chunks.append(self._build_chunk(current_chunk_paras, current_chunk_tokens))
                
                # Backtrack to build overlap
                overlap_paras = []
                overlap_tokens = 0
                for backtrack_para in reversed(current_chunk_paras):
                    bt_tokens = self.count_tokens(backtrack_para["text"])
                    if overlap_tokens + bt_tokens > overlap_size:
                        break
                    overlap_paras.insert(0, backtrack_para)
                    overlap_tokens += bt_tokens
                
                current_chunk_paras = overlap_paras
                current_chunk_tokens = overlap_tokens

            current_chunk_paras.append(para)
            current_chunk_tokens += para_tokens

        # Flush trailing paragraphs
        if current_chunk_paras:
            chunks.append(self._build_chunk(current_chunk_paras, current_chunk_tokens))

        return chunks

    def _build_chunk(self, paras: List[Dict[str, Any]], token_count: int) -> Dict[str, Any]:
        """
        Merge paragraph nodes into a single consolidated chunk with combined metadata.
        """
        combined_text = "\n\n".join([p["text"] for p in paras])
        
        # Resolve page boundaries
        pdf_start = paras[0]["pdf_page"]
        pdf_end = paras[-1]["pdf_page"]
        printed_start = paras[0]["printed_page"]
        printed_end = paras[-1]["printed_page"]

        # Content classification heuristic (code blocks or formulas)
        content_type = "prose"
        if "```" in combined_text:
            content_type = "code"
        elif "|" in combined_text and "-" in combined_text:
            content_type = "table"
        elif "$$" in combined_text or "\\" in combined_text:
            content_type = "formula"

        return {
            "content": combined_text,
            "token_count": token_count,
            "pdf_page_start": pdf_start,
            "pdf_page_end": pdf_end,
            "printed_page_start": printed_start,
            "printed_page_end": printed_end,
            "chapter": paras[0]["chapter"],
            "section": paras[0]["section"],
            "subsection": paras[0]["subsection"],
            "content_type": content_type
        }

chunker_service = SemanticChunkerService()
