import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.storage import get_storage
from app.models.document import Document, DocumentChunk, DocumentPage, DocumentStatus
from app.services.ingestion.chunker import chunk_pages
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.extractors import get_extractor
from app.services.ingestion.extractors.base import ExtractedPage, ExtractionError, UnsupportedFormatError

logger = logging.getLogger(__name__)

_EMPTY_PAGE_MESSAGE = "No extractable text found (document may be a scanned image PDF; OCR is out of scope)"


async def _mark_failed(db: AsyncSession, document_id: uuid.UUID, message: str) -> None:
    document = await db.get(Document, document_id)
    if document is None:
        return
    document.status = DocumentStatus.failed
    document.error_message = message[:2000]
    await db.commit()


async def ingest_document(db: AsyncSession, document_id: uuid.UUID) -> None:
    """Process a stored document: extract, clean, store pages, and chunk it.

    Standalone so both the Arq worker and tests can call it directly.
    """
    document = await db.get(Document, document_id)
    if document is None:
        return

    document.status = DocumentStatus.processing
    document.error_message = None
    await db.commit()

    settings = get_settings()
    storage = get_storage()

    try:
        path = await storage.open(document.storage_key)
        extractor = get_extractor(document.mime_type)
        pages = [ExtractedPage(p.page_number, clean_text(p.content)) for p in extractor.extract(path)]

        if pages and not any(p.content for p in pages):
            raise ExtractionError(_EMPTY_PAGE_MESSAGE)

        await db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))

        page_rows: list[DocumentPage] = []
        for page in pages:
            row = DocumentPage(
                document_id=document_id,
                page_number=page.page_number,
                content=page.content,
                char_count=len(page.content),
            )
            db.add(row)
            page_rows.append(row)
        await db.flush()

        page_id_by_number = {row.page_number: row.id for row in page_rows}

        for chunk in chunk_pages(pages, settings.chunk_size, settings.chunk_overlap):
            db.add(
                DocumentChunk(
                    document_id=document_id,
                    page_id=page_id_by_number.get(chunk.page_number),
                    content=chunk.content,
                    chunk_index=chunk.index,
                    token_count=chunk.token_count,
                )
            )

        document.page_count = len(page_rows)
        document.processed_at = datetime.now(UTC)
        document.status = DocumentStatus.ready
        await db.commit()

        logger.info("Document %s ingested (%d pages, processed)", document_id, len(page_rows))
    except UnsupportedFormatError as exc:
        logger.warning("Document %s unsupported: %s", document_id, exc)
        await _mark_failed(db, document_id, str(exc))
    except ExtractionError as exc:
        logger.warning("Document %s extraction failed: %s", document_id, exc)
        await _mark_failed(db, document_id, str(exc))
    except Exception as exc:
        logger.exception("Document %s ingestion failed", document_id)
        await _mark_failed(db, document_id, f"Ingestion failed: {exc}")
