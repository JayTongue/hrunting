"""
handlers/pdf.py
Extracts text from PDF files using pdfplumber.
Falls back page-by-page so a single bad page doesn't kill the whole doc.
"""

from pathlib import Path
from typing import Any


def extract(filepath: Path) -> dict[str, Any]:
    try:
        import pdfplumber
    except ImportError:
        return {
            "text": None,
            "metadata": {},
            "error": "pdfplumber not installed. Run: pip install pdfplumber",
        }

    pages_text: list[str] = []
    errors: list[str] = []
    metadata: dict[str, Any] = {}

    try:
        with pdfplumber.open(filepath) as pdf:
            metadata["page_count"] = len(pdf.pages)
            if pdf.metadata:
                metadata["pdf_metadata"] = {
                    k: str(v) for k, v in pdf.metadata.items() if v
                }

            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    pages_text.append(text)
                except Exception as exc:
                    errors.append(f"Page {i}: {exc}")
                    pages_text.append("")

    except Exception as exc:
        return {
            "text": None,
            "metadata": metadata,
            "error": f"Failed to open PDF: {exc}",
        }

    full_text = "\n\n".join(pages_text).strip()
    error_msg = "; ".join(errors) if errors else None

    return {
        "text": full_text,
        "metadata": metadata,
        "error": error_msg,
    }
