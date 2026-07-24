import os
import re
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
from app.core.config import settings

class PDFProcessorService:
    @staticmethod
    def extract_pages(file_path: str) -> List[Dict[str, Any]]:
        """
        Extract pages from a PDF.
        Returns:
            List[Dict] containing:
                "page_index": int (0-based)
                "text": str
                "printed_page": str (or None)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at {file_path}")

        doc = fitz.open(file_path)
        pages_data = []

        # First pass: extract text and detect printed page layout offsets
        page_texts = []
        for page_index in range(len(doc)):
            page = doc[page_index]
            text = page.get_text("text") or ""
            page_texts.append(text)

        # Detect printed logical page numbers (Roman or Arabic)
        printed_page_map = PDFProcessorService._detect_printed_page_numbers(page_texts)

        for page_index in range(len(doc)):
            page = doc[page_index]
            text = page_texts[page_index]
            
            # Check if OCR is required (scanned PDF page)
            if len(text.strip()) < 50:
                text = PDFProcessorService._run_ocr_fallback(page, page_index)

            # Clean headers/footers
            cleaned_text = PDFProcessorService._clean_page_noise(text)

            pages_data.append({
                "page_index": page_index,
                "text": cleaned_text,
                "printed_page": printed_page_map.get(page_index)
            })

        doc.close()
        return pages_data

    @staticmethod
    def _detect_printed_page_numbers(page_texts: List[str]) -> Dict[int, str]:
        """
        Attempt to parse printed page numbers from page footers/headers.
        Returns:
            Dict mapping page_index to logical printed string (e.g. '182', 'ix').
        """
        printed_map = {}
        
        # Standard patterns matching numbers at the bottom/top lines of page
        num_pattern = re.compile(r'^\s*([ivxldc]+|\d+)\s*$', re.IGNORECASE)
        
        for idx, text in enumerate(page_texts):
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                continue
            
            # Inspect first 2 and last 2 lines
            candidate_lines = lines[:2] + lines[-2:]
            found_num = None
            
            for line in candidate_lines:
                match = num_pattern.match(line)
                if match:
                    found_num = match.group(1)
                    break
                    
            if found_num:
                printed_map[idx] = found_num
            else:
                # Fallback to standard index-offset estimation if we find a clear start
                # Usually we just index pages incrementally.
                pass
                
        # Fill in logical offsets if we can determine a sequential run
        # E.g. if page index 15 reports printed page '1' and page 16 reports '2'
        # We can extrapolate offsets for contiguous pages.
        return printed_map

    @staticmethod
    def _clean_page_noise(text: str) -> str:
        """
        Strip boilerplate header/footer elements and repeated lines.
        """
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            line_strip = line.strip()
            # Skip empty lines
            if not line_strip:
                continue
            # Skip lines consisting only of page numbers
            if re.match(r'^\d+$', line_strip):
                continue
            # Skip common textbook headers (e.g. "Chapter X", "Database Systems")
            if re.match(r'^(chapter \d+|section \d+\.\d+)', line_strip, re.IGNORECASE):
                continue
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines)

    @staticmethod
    def _run_ocr_fallback(page: fitz.Page, page_index: int) -> str:
        """
        Render page to image and perform OCR using Tesseract if installed.
        """
        try:
            import pytesseract
            from PIL import Image
            import io
            
            # Attempt to set tesseract command path if configured
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            elif os.name == 'nt':
                # Common Windows Tesseract paths
                common_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break

            # Render page to PNG pixmap
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # upscale for better OCR accuracy
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Execute OCR
            ocr_text = pytesseract.image_to_string(img)
            return ocr_text
        except Exception as e:
            # If tesseract is not found/configured, print warning and return empty string
            print(f"[OCR Warning] Failed running OCR on page {page_index}: {e}")
            return ""
