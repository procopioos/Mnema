from pathlib import Path

from app.services.ingestion.extractors.base import ExtractedPage, Extractor


class TextExtractor(Extractor):
    def extract(self, path: Path) -> list[ExtractedPage]:
        content = path.read_text(encoding="utf-8", errors="replace")
        return [ExtractedPage(page_number=1, content=content)]
