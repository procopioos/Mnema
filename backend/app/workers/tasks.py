import uuid

from app.db.session import async_session
from app.services.ingestion.pipeline import ingest_document


async def process_document(ctx: dict, document_id: str) -> None:
    async with async_session() as session:
        await ingest_document(session, uuid.UUID(document_id))
