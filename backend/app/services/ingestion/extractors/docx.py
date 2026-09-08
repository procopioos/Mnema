from pathlib import Path

from docx import Document as DocxDocument

from app.services.ingestion.extractors.base import ExtractedPage, ExtractionError, Extractor


class DocxExtractor(Extractor):
    def extract(self, path: Path) -> list[ExtractedPage]:
        try:
            doc = DocxDocument(path)
        except Exception as exc:
            raise ExtractionError(f"Could not read DOCX: {exc}") from exc
        content = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return [ExtractedPage(page_number=1, content=content)]
