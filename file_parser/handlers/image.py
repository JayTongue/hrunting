"""
handlers/image.py
Extracts text from images via Tesseract OCR.

Preprocessing:
  1. EXIF orientation correction
  2. Denoise + adaptive threshold + deskew + 2x upscale

Metadata includes handwriting_detected (bool) based on two signals:
  - Connected component height CV (printed text is uniform; handwriting is not)
  - Mean Tesseract word confidence (printed scores high; handwriting scores low)

Requirements:
    pip install pytesseract Pillow opencv-python-headless
    # Windows Tesseract binary: winget install UB-Mannheim.TesseractOCR
"""

from pathlib import Path
from typing import Any

_TESS_CMD = r"C:\Users\jtung\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
_TESS_CONFIG = "--oem 1 --psm 6"

# Thresholds for handwriting classification
_CV_H_THRESHOLD = 0.30    # connected-component height CV above this → handwriting
_CONF_THRESHOLD = 90.0    # mean Tesseract confidence below this → handwriting


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _exif_rotate(img):
    from PIL import ImageOps
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def _deskew(img):
    import numpy as np

    scale = max(1, max(img.width, img.height) // 800)
    small = img.resize((img.width // scale, img.height // scale))

    def _score(angle):
        rotated = small.rotate(angle, expand=False, fillcolor=255)
        arr = np.array(rotated)
        binary = (arr < 128).astype(float)
        return binary.sum(axis=1).var()

    coarse = range(-20, 21, 2)
    best = max(coarse, key=_score)
    fine = [best + i * 0.5 for i in range(-4, 5)]
    best = max(fine, key=_score)

    if abs(best) < 0.5:
        return img
    return img.rotate(best, expand=True, fillcolor=255)


def _tess_preprocess(img):
    import cv2
    import numpy as np
    from PIL import Image

    arr = np.array(img.convert("L"))
    arr = cv2.fastNlMeansDenoising(arr, h=10, templateWindowSize=7, searchWindowSize=21)
    arr = cv2.adaptiveThreshold(
        arr, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=15,
    )
    pil = Image.fromarray(arr)
    pil = _deskew(pil)
    return pil.resize((pil.width * 2, pil.height * 2))


# ---------------------------------------------------------------------------
# Handwriting detection
# ---------------------------------------------------------------------------

def _component_height_cv(img) -> float | None:
    """
    Coefficient of variation of character-blob heights.
    Printed text is typeset at uniform size → low CV (~0.15-0.35).
    Handwriting varies in size and stroke → high CV (~0.4-0.8).
    """
    import cv2
    import numpy as np

    arr = np.array(img.convert("L"))
    _, binary = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    heights = []
    for i in range(1, num_labels):  # label 0 is background
        area = stats[i, cv2.CC_STAT_AREA]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        w = stats[i, cv2.CC_STAT_WIDTH]
        # Keep blobs that look like individual characters
        if 30 < area < 10_000 and 5 < h < img.height * 0.3 and w < img.width * 0.5:
            heights.append(h)

    if len(heights) < 10:
        return None
    mean_h = float(np.mean(heights))
    return float(np.std(heights)) / mean_h if mean_h > 0 else None


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def extract(filepath: Path) -> dict[str, Any]:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except ImportError:
        return {
            "text": None,
            "metadata": {},
            "error": "Pillow not installed. Run: pip install Pillow",
        }

    try:
        import pytesseract
        from pytesseract import Output
        pytesseract.pytesseract.tesseract_cmd = _TESS_CMD
    except ImportError:
        return {
            "text": None,
            "metadata": {},
            "error": "pytesseract not installed. Run: pip install pytesseract",
        }

    # Open — capture format/EXIF before any conversion
    try:
        img = Image.open(str(filepath))
        original_format = img.format
        if original_format == "MPO":
            img.seek(0)
    except Exception as exc:
        return {
            "text": None,
            "metadata": {},
            "error": f"Failed to open image: {exc}",
        }

    metadata: dict[str, Any] = {
        "format": original_format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
        "ocr_engine": "tesseract",
    }
    try:
        exif_data = img._getexif()  # type: ignore[attr-defined]
        if exif_data:
            exif = {
                TAGS.get(tag_id, tag_id): str(value)
                for tag_id, value in exif_data.items()
                if tag_id in TAGS
            }
            useful = {
                "DateTime", "Make", "Model", "Software",
                "ImageDescription", "Artist", "Copyright",
                "GPSInfo", "Orientation",
            }
            metadata["exif"] = {k: v for k, v in exif.items() if k in useful}
    except (AttributeError, Exception):
        pass

    img = _exif_rotate(img)

    # Handwriting signal 1: component height CV (run before binarisation)
    cv_h = _component_height_cv(img)

    # Preprocess for Tesseract
    try:
        processed = _tess_preprocess(img)
    except Exception as exc:
        metadata["preprocess_error"] = str(exc)
        processed = img.convert("L")

    # Run Tesseract — use image_to_data to get text + per-word confidence
    try:
        data = pytesseract.image_to_data(
            processed, config=_TESS_CONFIG, output_type=Output.DICT
        )
    except pytesseract.TesseractNotFoundError:
        return {
            "text": None,
            "metadata": metadata,
            "error": "Tesseract binary not found. Install from https://github.com/UB-Mannheim/tesseract/wiki",
        }
    except Exception as exc:
        return {
            "text": None,
            "metadata": metadata,
            "error": f"OCR failed: {exc}",
        }

    # Reconstruct text preserving line structure
    line_words: dict[tuple, list[str]] = {}
    word_confs: list[float] = []
    for i in range(len(data["text"])):
        conf = int(data["conf"][i])
        text = data["text"][i].strip()
        if conf > 0 and text:
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            line_words.setdefault(key, []).append(text)
            word_confs.append(conf)

    text = "\n".join(" ".join(words) for words in line_words.values())
    mean_conf = sum(word_confs) / len(word_confs) if word_confs else None

    # Handwriting signal 2: mean Tesseract confidence
    hw_by_cv = cv_h is not None and cv_h > _CV_H_THRESHOLD
    hw_by_conf = mean_conf is not None and mean_conf < _CONF_THRESHOLD
    handwriting_detected = hw_by_cv or hw_by_conf

    metadata["handwriting_detected"] = handwriting_detected
    metadata["handwriting_signals"] = {
        "component_height_cv": round(cv_h, 3) if cv_h is not None else None,
        "mean_ocr_confidence": round(mean_conf, 1) if mean_conf is not None else None,
    }

    return {
        "text": text.strip(),
        "metadata": metadata,
        "error": None,
    }
