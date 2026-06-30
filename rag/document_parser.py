import os
from typing import List, Dict, Any
from loguru import logger
import pypdf
import docx

class DocumentParser:
    """Utility class to parse PDF, DOCX, MD, and TXT files into raw text."""

    @staticmethod
    def parse_file(file_path: str) -> str:
        """Parses a file based on its extension and returns clean text."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return DocumentParser._parse_pdf(file_path)
        elif ext == ".docx":
            return DocumentParser._parse_docx(file_path)
        elif ext in (".md", ".txt"):
            return DocumentParser._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        """Extracts text from a PDF file."""
        text = []
        try:
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise RuntimeError(f"PDF parsing error: {e}")

    @staticmethod
    def _parse_docx(file_path: str) -> str:
        """Extracts text from a DOCX file."""
        try:
            doc = docx.Document(file_path)
            text = [para.text for para in doc.paragraphs]
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Failed to parse DOCX {file_path}: {e}")
            raise RuntimeError(f"DOCX parsing error: {e}")

    @staticmethod
    def _parse_text(file_path: str) -> str:
        """Extracts text from a text or markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to parse text file {file_path}: {e}")
            raise RuntimeError(f"Text file parsing error: {e}")


class RecursiveCharacterTextSplitter:
    """Splits a document recursively into chunks using delimiters."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Splits the input text into chunks of maximum self.chunk_size."""
        if not text:
            return []

        chunks = []
        words = text.split(" ")
        current_chunk = []
        current_size = 0

        # Simple split logic that behaves like character splitter with overlap
        for word in words:
            # Approximate character count (word + space)
            word_size = len(word) + 1
            if current_size + word_size > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                # Create overlap: keep trailing words
                overlap_size = 0
                overlap_words = []
                for w in reversed(current_chunk):
                    if overlap_size + len(w) + 1 > self.chunk_overlap:
                        break
                    overlap_words.insert(0, w)
                    overlap_size += len(w) + 1
                current_chunk = overlap_words
                current_size = sum(len(w) + 1 for w in current_chunk)

            current_chunk.append(word)
            current_size += word_size

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return [c.strip() for c in chunks if c.strip()]
