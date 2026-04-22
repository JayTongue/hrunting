"""
server.py
FastAPI wrapper around file_parser.parser.

Usage:
    uvicorn server:app --workers 4
    uvicorn server:app --workers 4 --host 0.0.0.0 --port 8000
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from file_parser.parser import parse

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="File Parser API",
    description="Extract text and metadata from documents.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    filepath: str

    @field_validator("filepath")
    @classmethod
    def filepath_must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("filepath must not be empty")
        return v.strip()


class ParseResponse(BaseModel):
    filepath: str
    filename: str
    extension: str
    size_bytes: Optional[int]
    modified: Optional[str]
    text: Optional[Union[str, Dict[str, Any]]]  # dict for xlsx (sheet -> text)
    metadata: Dict[str, Any]
    error: Optional[str]

# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    "FILE_NOT_FOUND":        404,
    "UNSUPPORTED_EXTENSION": 415,
    "HANDLER_ERROR":         500,
}

def _error_code(error: str) -> str:
    """Map the error string from parser.parse() to a stable error code."""
    if "File not found" in error:
        return "FILE_NOT_FOUND"
    if "Unsupported extension" in error:
        return "UNSUPPORTED_EXTENSION"
    return "HANDLER_ERROR"

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/parse", response_model=ParseResponse)
def parse_file(request: ParseRequest) -> ParseResponse:
    """
    Parse a file at the given absolute path and return extracted text
    and metadata.

    Error codes
    -----------
    404  File not found at the given path.
    415  File extension has no registered handler.
    500  Handler raised an unhandled exception.
    """
    result = parse(request.filepath)

    if result.get("error"):
        code = _error_code(result["error"])
        status = _STATUS_MAP.get(code, 500)
        raise HTTPException(status_code=status, detail={
            "error_code": code,
            "message": result["error"],
            "filepath": result.get("filepath"),
        })

    return ParseResponse(**result)