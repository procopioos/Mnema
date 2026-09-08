from dataclasses import dataclass

from app.services.ingestion.extractors.base import ExtractedPage


@dataclass
class ChunkResult:
    page_number: int
    index: int
    content: str
    token_count: int


def chunk_text(content: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    words = content.split()
    if not words:
        return []
    chunks: list[str] = []
    n = len(words)
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start += step
    return chunks


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[ChunkResult]:
    results: list[ChunkResult] = []
    index = 0
    for page in pages:
        for text in chunk_text(page.content, chunk_size, overlap):
            results.append(
                ChunkResult(
                    page_number=page.page_number,
                    index=index,
                    content=text,
                    token_count=len(text.split()),
                )
            )
            index += 1
    return results
