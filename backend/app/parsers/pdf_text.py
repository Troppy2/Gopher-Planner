"""Plain-text extraction from PDF bytes, separate from parsing. Extraction libraries are kept quiet."""
import io
import logging

for name in ("pdfminer", "pdfplumber"):
    # Debug logs from extraction libraries can include document text; never emit them.
    logging.getLogger(name).setLevel(logging.WARNING)


class PdfUnreadable(ValueError):
    pass


def extract_pdf_text(data):
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(data)) as document:
            return "\n".join(page.extract_text() or "" for page in document.pages)
    except Exception as error:  # noqa: BLE001 - any parser failure is an unreadable upload
        raise PdfUnreadable("The PDF could not be read") from error
