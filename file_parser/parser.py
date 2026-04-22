"""
file_parser/parser.py
Entry point. Pass a filepath, get back a normalized dict.
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .handlers import pdf, docx, doc, xlsx, image, plaintext, rtf

# ---------------------------------------------------------------------------
# Extension registry
# ---------------------------------------------------------------------------

HANDLERS = {
    # PDF
    ".pdf": pdf.extract,
    # Word (modern)
    ".docx": docx.extract,
    # Word (legacy binary)
    ".doc": doc.extract,
    # Excel
    ".xlsx": xlsx.extract,
    ".xls": xlsx.extract,
    # Images (OCR)
    ".jpg": image.extract,
    ".jpeg": image.extract,
    ".png": image.extract,
    ".tiff": image.extract,
    ".tif": image.extract,
    ".bmp": image.extract,
    ".webp": image.extract,
    # RTF
    ".rtf": rtf.extract,
    # Plain text family
    ".txt": plaintext.extract,
    ".md": plaintext.extract,
    ".markdown": plaintext.extract,
    ".csv": plaintext.extract,
    ".tsv": plaintext.extract,
    ".log": plaintext.extract,
    ".json": plaintext.extract,
    ".xml": plaintext.extract,
    ".html": plaintext.extract,
    ".htm": plaintext.extract,
    ".yaml": plaintext.extract,
    ".yml": plaintext.extract,
    ".toml": plaintext.extract,
    ".ini": plaintext.extract,
    ".cfg": plaintext.extract,
    ".py": plaintext.extract,
    ".js": plaintext.extract,
    ".ts": plaintext.extract,
    ".css": plaintext.extract,
    ".sh": plaintext.extract,
    ".bat": plaintext.extract,
    ".ps1": plaintext.extract,
    ".sql": plaintext.extract,
    ".r": plaintext.extract,
}


def _base_metadata(filepath: Path) -> Dict[str, Any]:
    """File-level metadata available for every format."""
    if not filepath.exists():
        return {
            "filepath": str(filepath.resolve()),
            "filename": filepath.name,
            "extension": filepath.suffix.lower(),
            "size_bytes": None,
            "modified": None,
        }
    stat = filepath.stat()
    return {
        "filepath": str(filepath.resolve()),
        "filename": filepath.name,
        "extension": filepath.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified": time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime)
        ),
    }


def parse(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse any supported file and return a normalized result dict.

    Returns
    -------
    {
        "filepath":  str,
        "filename":  str,
        "extension": str,
        "size_bytes": int,
        "modified":  str (ISO-8601),
        "text":      str | dict,   # dict for xlsx (sheet_name -> text)
        "metadata":  dict,         # format-specific extras
        "error":     str | None,
    }
    """
    path = Path(filepath)

    if not path.exists():
        return {
            **_base_metadata(path),
            "text": None,
            "metadata": {},
            "error": f"File not found: {filepath}",
        }

    ext = path.suffix.lower()
    handler = HANDLERS.get(ext)

    base = _base_metadata(path)

    if handler is None:
        return {
            **base,
            "text": None,
            "metadata": {},
            "error": f"Unsupported extension: '{ext}'. No handler registered.",
        }

    try:
        result = handler(path)
        return {
            **base,
            "text": result.get("text"),
            "metadata": result.get("metadata", {}),
            "error": result.get("error"),
        }
    except Exception as exc:
        return {
            **base,
            "text": None,
            "metadata": {},
            "error": f"Unhandled exception in {ext} handler: {type(exc).__name__}: {exc}",
        }
