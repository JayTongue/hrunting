"""
handlers/plaintext.py
Reads plain text files with automatic encoding detection.
Falls back through common encodings before giving up.
"""

from pathlib import Path
from typing import Any, Optional

# Encodings to try in order
_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "utf-16"]


def extract(filepath: Path) -> dict[str, Any]:
    raw: bytes
    try:
        raw = filepath.read_bytes()
    except Exception as exc:
        return {
            "text": None,
            "metadata": {},
            "error": f"Could not read file: {exc}",
        }

    # Optional: use chardet for better encoding detection
    detected_encoding: str | None = None
    try:
        import chardet
        result = chardet.detect(raw)
        if result and result.get("confidence", 0) > 0.7:
            detected_encoding = result["encoding"]
    except ImportError:
        pass  # chardet is optional

    encodings_to_try = (
        [detected_encoding] + _ENCODINGS if detected_encoding else _ENCODINGS
    )

    text: Optional[str] = None
    used_encoding: Optional[str] = None

    for enc in encodings_to_try:
        if enc is None:
            continue
        try:
            text = raw.decode(enc)
            used_encoding = enc
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        # Last resort: decode as utf-8 replacing errors
        text = raw.decode("utf-8", errors="replace")
        used_encoding = "utf-8 (with replacement)"

    metadata: dict[str, Any] = {
        "encoding": used_encoding,
        "line_count": text.count("\n") + 1,
        "char_count": len(text),
    }

    return {
        "text": text,
        "metadata": metadata,
        "error": None,
    }
