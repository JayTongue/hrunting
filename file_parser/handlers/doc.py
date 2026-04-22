"""
handlers/doc.py
Extracts text from legacy binary .doc files using olefile.

olefile gives us access to the raw OLE streams. The Word Document stream
contains the text interleaved with binary control bytes — we strip the
non-printable bytes and return what's left. This is imperfect but is the
best available pure-Python option for .doc without LibreOffice.

If you have LibreOffice installed, a more reliable approach is:
    soffice --headless --convert-to docx file.doc
then parse the resulting .docx with the docx handler.
"""

from pathlib import Path
from typing import Any
import re


def _strip_binary(data: bytes) -> str:
    """
    Pull printable ASCII and common unicode text out of raw Word stream bytes.
    Strips NUL bytes and non-printable control chars, keeps newlines and tabs.
    """
    # Decode as latin-1 (lossless for all byte values) then filter
    text = data.decode("latin-1", errors="replace")
    # Keep printable chars, newlines, tabs; drop the rest
    cleaned = re.sub(r"[^\x20-\x7E\x80-\xFF\n\t]", " ", text)
    # Collapse runs of whitespace/spaces but preserve newlines
    lines = [re.sub(r" {2,}", " ", line).strip() for line in cleaned.splitlines()]
    # Drop lines that are pure noise (less than 3 printable chars)
    lines = [l for l in lines if len(re.sub(r"\s", "", l)) >= 3]
    return "\n".join(lines)


def extract(filepath: Path) -> dict[str, Any]:
    try:
        import olefile
    except ImportError:
        return {
            "text": None,
            "metadata": {},
            "error": "olefile not installed. Run: pip install olefile",
        }

    try:
        if not olefile.isOleFile(str(filepath)):
            return {
                "text": None,
                "metadata": {},
                "error": "File does not appear to be a valid OLE/DOC file.",
            }

        ole = olefile.OleFileIO(str(filepath))
    except Exception as exc:
        return {
            "text": None,
            "metadata": {},
            "error": f"Failed to open DOC file: {exc}",
        }

    metadata: dict[str, Any] = {"warning": "Legacy .doc extraction is approximate."}
    text = None
    error = None

    try:
        # The main text lives in the 'WordDocument' stream
        if ole.exists("WordDocument"):
            raw = ole.openstream("WordDocument").read()
            text = _strip_binary(raw)
        else:
            error = "No 'WordDocument' stream found — may not be a Word .doc file."

        # Grab summary metadata if present
        if ole.exists("\x05SummaryInformation"):
            try:
                props = ole.get_metadata()
                for attr in ("author", "title", "subject", "last_saved_by"):
                    val = getattr(props, attr, None)
                    if val:
                        metadata[attr] = (
                            val.decode("utf-8", errors="replace")
                            if isinstance(val, bytes)
                            else str(val)
                        )
            except Exception:
                pass

    except Exception as exc:
        error = f"Error reading DOC streams: {exc}"
    finally:
        ole.close()

    return {
        "text": text,
        "metadata": metadata,
        "error": error,
    }
