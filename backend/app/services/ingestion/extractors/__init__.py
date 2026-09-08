from app.domain.formats import EXTENSION_TO_MIME
from app.services.ingestion.extractors.base import Extractor, UnsupportedFormatError
from app.services.ingestion.extractors.docx import DocxExtractor
from app.services.ingestion.extractors.pdf import PdfExtractor
from app.services.ingestion.extractors.text import TextExtractor

_MIME_TO_EXTRACTOR: dict[str, type[Extractor]] = {
    EXTENSION_TO_MIME["pdf"]: PdfExtractor,
    EXTENSION_TO_MIME["docx"]: DocxExtractor,
    EXTENSION_TO_MIME["txt"]: TextExtractor,
    EXTENSION_TO_MIME["md"]: TextExtractor,
}


def get_extractor(mime_type: str) -> Extractor:
    extractor_cls = _MIME_TO_EXTRACTOR.get(mime_type)
    if extractor_cls is None:
        raise UnsupportedFormatError(f"Unsupported MIME type: {mime_type}")
    return extractor_cls()
