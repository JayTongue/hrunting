"""
handlers/rtf.py
Extracts text from RTF files using striprtf.
"""

from pathlib import Path
from typing import Any

_ENCODINGS = ["utf-8", "latin-1", "cp1252"]


def extract(filepath: Path) -> dict[str, Any]:
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        return {
            "text": None,
            "metadata": {},
            "error": "striprtf not installed. Run: pip install striprtf",
        }

    try:
        raw = filepath.read_bytes()
    except Exception as exc:
        return {
            "text": None,
            "metadata": {},
            "error": f"Could not read file: {exc}",
        }

    content: str | None = None
    for enc in _ENCODINGS:
        try:
            content = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        content = raw.decode("utf-8", errors="replace")

    try:
        text = rtf_to_text(content)
    except Exception as exc:
        return {
            "text": None,
            "metadata": {},
            "error": f"RTF parsing failed: {exc}",
        }

    return {
        "text": text.strip(),
        "metadata": {
            "line_count": text.count("\n") + 1,
            "char_count": len(text),
        },
        "error": None,
    }
