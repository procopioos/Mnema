from pathlib import Path

import fitz

from app.services.ingestion.extractors.base import ExtractedPage, ExtractionError, Extractor


class PdfExtractor(Extractor):
    def extract(self, path: Path) -> list[ExtractedPage]:
        pages: list[ExtractedPage] = []
        try:
            with fitz.open(path) as doc:
                for number, page in enumerate(doc, start=1):
                    pages.append(ExtractedPage(page_number=number, content=page.get_text("text")))
        except Exception as exc:
            raise ExtractionError(f"Could not read PDF: {exc}") from exc
        return pages
