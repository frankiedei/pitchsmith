"""Document parsing: extract raw context text from uploaded .pdf and .txt files
(artist bios, quotes, background notes). PDF via pypdf; text decoded directly.
"""
import logging

log = logging.getLogger("pitchsmith.parsing")

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


def extract_text(filename: str, data: bytes) -> str:
    """Pull plain text out of an uploaded file by extension. Unknown types are
    decoded best-effort as UTF-8 so a stray .md or .rtf still yields something."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    # .txt and everything else: best-effort decode
    return data.decode("utf-8", errors="replace").strip()


def _extract_pdf(data: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed — cannot read PDF uploads")
    import io

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # a single bad page shouldn't kill the upload
            log.exception("failed to extract a PDF page")
    return "\n\n".join(p.strip() for p in parts if p.strip()).strip()
