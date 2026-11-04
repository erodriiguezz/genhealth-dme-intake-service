"""PDF upload checks. Nothing here logs filenames or content: both can be PHI."""

import hashlib
import io
import re
from dataclasses import dataclass
from typing import BinaryIO

from pypdf import PdfReader

from app.errors import ApiError

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 100
MAX_FILENAME = 255
_CHUNK = 1024 * 1024
_UNSAFE = re.compile(r"[\x00-\x1f\x7f\"\\/]")


@dataclass(frozen=True)
class PdfUpload:
    filename: str
    content: bytes
    sha256: str
    page_count: int

    @property
    def size_bytes(self) -> int:
        return len(self.content)


def sanitize_filename(raw: str | None) -> str:
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = _UNSAFE.sub("", name).strip().lstrip(".")
    return name[:MAX_FILENAME] or "document.pdf"


def read_capped(stream: BinaryIO) -> bytes:
    limit = MAX_BYTES
    buf = bytearray()
    while chunk := stream.read(_CHUNK):
        buf += chunk
        if len(buf) > limit:
            raise ApiError(413, "file_too_large", "The PDF is larger than 20 MB.")
    return bytes(buf)


def check_pdf(content: bytes) -> int:
    """Return the page count, or raise 415 (not a PDF) / 422 (unreadable PDF)."""
    if not content.startswith(b"%PDF-"):
        raise ApiError(415, "unsupported_media_type", "Only PDF files are accepted.")
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise ApiError(422, "invalid_pdf", "Encrypted PDFs are not supported.")
        pages = len(reader.pages)
    except ApiError:
        raise
    except Exception:
        raise ApiError(422, "invalid_pdf", "The PDF could not be read.") from None
    if pages < 1 or pages > MAX_PAGES:
        raise ApiError(422, "invalid_pdf", f"The PDF must have 1 to {MAX_PAGES} pages.")
    return pages


def load_upload(stream: BinaryIO, filename: str | None) -> PdfUpload:
    content = read_capped(stream)
    pages = check_pdf(content)
    return PdfUpload(
        filename=sanitize_filename(filename),
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        page_count=pages,
    )
