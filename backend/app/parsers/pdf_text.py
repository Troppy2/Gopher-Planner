"""Plain-text extraction from PDF bytes, separate from parsing. Extraction libraries are kept quiet."""
import io
import logging

for name in ("pdfminer", "pdfplumber"):
    # Debug logs from extraction libraries can include document text; never emit them.
    logging.getLogger(name).setLevel(logging.WARNING)


MAX_PAGES = 15  # matches the OCR page limit; an audit is a handful of pages
MAX_CHARS = 200_000  # far above any real audit; bounds memory for hostile files


class PdfUnreadable(ValueError):
    pass


def extract_pdf_text(data):
    """Text of the first MAX_PAGES pages, stopping once MAX_CHARS is reached."""
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(data)) as document:
            parts, total = [], 0
            for page in document.pages[:MAX_PAGES]:
                text = page.extract_text() or ""
                parts.append(text)
                total += len(text) + 1
                page.close()
                if total >= MAX_CHARS:
                    break
            return "\n".join(parts)[:MAX_CHARS]
    except Exception as error:  # noqa: BLE001 - any parser failure is an unreadable upload
        raise PdfUnreadable("The PDF could not be read") from error
