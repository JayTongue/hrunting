#!/usr/bin/env python3
"""
Usage:
    python parse.py path/to/file.pdf
    python parse.py path/to/spreadsheet.xlsx
    python parse.py path/to/image.jpg

Prints the result dict as formatted JSON.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from file_parser import parse


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse.py <filepath>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    result = parse(filepath)

    # Pretty-print, handling non-serializable types gracefully
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
