from dataclasses import dataclass
from pathlib import Path


class ExtractionError(Exception):
    """Raised when a document cannot be extracted."""


class UnsupportedFormatError(ExtractionError):
    """Raised when no extractor exists for the document type."""


@dataclass
class ExtractedPage:
    page_number: int
    content: str


class Extractor:
    def extract(self, path: Path) -> list[ExtractedPage]:
        raise NotImplementedError
