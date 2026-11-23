"""Text recognition for image-only (scanned) PDFs, run locally. Nothing leaves the server.

RapidOCR runs PaddleOCR's detection and recognition models through ONNX Runtime on the CPU, which
copes with skewed, blurred and speckled scans far better than classic Tesseract. Pages are rendered
with pypdfium2. Recognized text is returned to the caller and never logged.
"""
import io
import logging
import re
import threading

for name in ("RapidOCR", "rapidocr"):
    # Its debug and info output can echo recognized text; never emit it.
    logging.getLogger(name).setLevel(logging.WARNING)

MAX_PAGES = 15  # a transcript is a few pages; this bounds request time
RENDER_SCALE = 3  # 216 DPI: enough detail for small print without slowing recognition much
MAX_PAGE_PIXELS = 25_000_000  # a letter page at RENDER_SCALE is about 4.5 MP; larger pages are scaled down
MAX_TOTAL_PIXELS = 120_000_000  # stops a document of oversized pages from exhausting memory or time

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    """Load the models once per process; later calls reuse them."""
    global _engine
    with _engine_lock:
        if _engine is None:
            from rapidocr import RapidOCR

            _engine = RapidOCR()
            for name in ("RapidOCR", "rapidocr"):
                logging.getLogger(name).setLevel(logging.WARNING)
        return _engine


def recognize_page(image):
    """Return (boxes, texts) for one page image."""
    result = _get_engine()(image)
    if result is None or result.boxes is None or not result.txts:
        return [], []
    return [box.tolist() if hasattr(box, "tolist") else box for box in result.boxes], list(result.txts)


def lines_from_boxes(boxes, texts):
    """Rebuild reading-order lines: group boxes whose vertical centers overlap, then sort each line left to right."""
    items = []
    for box, text in zip(boxes, texts):
        ys = [point[1] for point in box]
        xs = [point[0] for point in box]
        items.append({"top": min(ys), "bottom": max(ys), "left": min(xs), "text": text.strip()})
    items = [item for item in items if item["text"]]
    items.sort(key=lambda item: (item["top"] + item["bottom"]) / 2)
    lines = []
    for item in items:
        center = (item["top"] + item["bottom"]) / 2
        height = item["bottom"] - item["top"]
        if lines:
            current = lines[-1]
            if abs(center - current["center"]) <= max(height, current["height"]) / 2:
                current["items"].append(item)
                continue
        lines.append({"center": center, "height": height, "items": [item]})
    return [" ".join(item["text"] for item in sorted(line["items"], key=lambda item: item["left"]))
            for line in lines]


_SPACING = (
    # "CSCI 1133Introduction" -> "CSCI 1133 Introduction" (a course suffix letter stays attached)
    (re.compile(r"\b([A-Z]{2,6} \d{4}[A-Z]?)(?=[A-Z][a-z])"), r"\1 "),
    # "Computing4.0" / "CalculusI4.0" -> space before the credits
    (re.compile(r"(?<=[A-Za-z)])(?=\d{1,2}\.\d\b)"), " "),
    # "4.0A-" -> "4.0 A-" (credits run into the grade at the end of a row)
    (re.compile(r"(\d\.\d)(?=(?:A-?|B[+-]?|C[+-]?|D\+?|F|S|N|W|I|IP)$)"), r"\1 "),
)


def restore_spacing(line):
    """OCR often drops the gaps between table columns; put them back where a row's fields meet."""
    for pattern, replacement in _SPACING:
        line = pattern.sub(replacement, line)
    return line


def ocr_pdf_text(data):
    """Recognize text on up to MAX_PAGES pages and return it as newline-separated lines."""
    import pypdfium2

    document = pypdfium2.PdfDocument(io.BytesIO(data))
    try:
        output, budget = [], MAX_TOTAL_PIXELS
        for index in range(min(len(document), MAX_PAGES)):
            page = document[index]
            try:
                width, height = page.get_size()  # points
                scale = min(RENDER_SCALE, (MAX_PAGE_PIXELS / max(width * height, 1.0)) ** 0.5)
                pixels = width * height * scale * scale
                if pixels > budget:
                    break
                budget -= pixels
                image = page.render(scale=scale).to_pil().convert("RGB")
            finally:
                page.close()
            recognized = recognize_page(image)
            if not recognized:
                continue
            boxes, texts = recognized
            output.extend(restore_spacing(line) for line in lines_from_boxes(boxes, texts))
        return "\n".join(output)
    finally:
        document.close()
