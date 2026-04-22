# Hrunting

#### A Universal File Parser

Justin Tung, 2026

-----------------------------

    And another item lent by Unferth
    at that moment of need was of no small importance:
    the brehon handed him a hilted weapon,
    a rare and ancient sword named Hrunting.
    The iron blade with its ill-boding patterns
    had been tempered in blood. It had never failed
    the hand of anyone who hefted it in battle,
    anyone who had fought and faced the worst
    in the gap of danger. This was not the first time
    it had been called to perform heroic feats.

-----------------------------

# Overview

This is a local Flask-based FastAPI server that acts as an access-anywhere file parsing API. It currently takes the following formats:

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

If you have files in any of these formats and want an api you can send a local filepath to in order to return the text of that document, then hrunting may fit your use case. 

# Usage

To deploy the server, cd to where server.py is, and run 

    uv run uvicorn server:app --reload   

Then to interact with the server, interact with it

    import requests

    response = requests.post(
        "http://127.0.0.1:8000/parse",
        json={"filepath": "/absolute/path/to/file.pdf"}
    )
    result = response.json()

In return you will get a JSON object:

    {
        **base # an unpacked dict of the basic info pertaining to the file at the path directed.
        "text": # the discovered text
        "metadata": # the document metadata,
        "error": # error message, if there was one
    }

# Tech Notes

This code currently runs OCR on image files. It uses <a href="https://github.com/tesseract-ocr/tesseract">Tesseract</a>, an open-source OCR engine. Note that this works well for printed text, but does not perform very well with handwritten text. 

Another limitation is that if there are mixed processing requirements (e.g. a PDF with a text-encoded coversheet but also has a photo of a handwritten form), it will only process according to the type of file.