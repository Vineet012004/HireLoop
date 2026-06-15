"""Resume file parser — extracts raw text from PDF and DOCX uploads."""
import io
import pdfplumber
from docx import Document


def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file given its raw bytes."""
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def parse_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file given its raw bytes."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()


def parse_resume(file_bytes: bytes, filename: str) -> str:
    """
    Dispatch to the right parser based on file extension.

    Raises:
        ValueError: If the file type is not supported.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return parse_pdf(file_bytes)
    elif lower.endswith(".docx"):
        return parse_docx(file_bytes)
    elif lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore").strip()
    else:
        raise ValueError(f"Unsupported file type: {filename}. Upload a PDF, DOCX, or TXT file.")
