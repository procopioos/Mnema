import uuid
from io import BytesIO

import fitz
from docx import Document as DocxDocument
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document import Document, DocumentChunk
from app.services.ingestion.pipeline import ingest_document
from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_pdf() -> bytes:
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Employee Handbook Page One", fontsize=12)
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Employees receive 25 vacation days per year", fontsize=12)
    return doc.tobytes()


async def _register_and_workspace(client: AsyncClient, register_user: RegisterCallable) -> tuple[dict, dict]:
    data = await register_user()
    workspaces = (await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))).json()
    return data, workspaces[0]


async def _upload(
    client: AsyncClient,
    token: str,
    workspace_id: str,
    *,
    name: str = "handbook.pdf",
    content: bytes | None = None,
    mime: str = "application/pdf",
) -> dict:
    files = {"file": (name, content or _make_pdf(), mime)}
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=_auth(token),
        files=files,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_upload_lists_and_ingests(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    doc = await _upload(client, user["access_token"], workspace["id"])

    assert doc["status"] == "pending"
    assert doc["filename"] == "handbook.pdf"
    assert doc["mime_type"] == "application/pdf"
    assert doc["workspace_id"] == workspace["id"]

    listed = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/documents",
            headers=_auth(user["access_token"]),
        )
    ).json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == doc["id"]

    await ingest_document(db_session, uuid.UUID(doc["id"]))

    updated = (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(user["access_token"]))).json()
    assert updated["status"] == "ready"
    assert updated["page_count"] == 2

    pages = (await client.get(f"/api/v1/documents/{doc['id']}/pages", headers=_auth(user["access_token"]))).json()
    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert "Employee Handbook" in pages[0]["content"]
    page = (await client.get(f"/api/v1/documents/{doc['id']}/pages/2", headers=_auth(user["access_token"]))).json()
    assert "vacation days" in page["content"]

    chunk_count = await db_session.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(doc["id"]))
    )
    assert chunk_count and chunk_count > 0


async def test_file_endpoint_streams_original(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    content = _make_pdf()
    doc = await _upload(client, user["access_token"], workspace["id"], content=content)

    response = await client.get(f"/api/v1/documents/{doc['id']}/file", headers=_auth(user["access_token"]))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content == content


async def test_docx_roundtrip(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    buffer = BytesIO()
    docx = DocxDocument()
    docx.add_paragraph("Standard payment terms are net 30 days from invoice.")
    docx.save(buffer)
    doc = await _upload(
        client,
        user["access_token"],
        workspace["id"],
        name="terms.docx",
        content=buffer.getvalue(),
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    await ingest_document(db_session, uuid.UUID(doc["id"]))
    updated = (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(user["access_token"]))).json()
    assert updated["status"] == "ready"
    assert updated["page_count"] == 1
    pages = (await client.get(f"/api/v1/documents/{doc['id']}/pages", headers=_auth(user["access_token"]))).json()
    assert "net 30 days" in pages[0]["content"]


async def test_unsupported_extension_rejected(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    response = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/documents",
        headers=_auth(user["access_token"]),
        files={"file": ("archive.rar", b"Rar!", "application/x-rar")},
    )
    assert response.status_code == 415


async def test_oversized_upload_rejected(
    client: AsyncClient,
    register_user: RegisterCallable,
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    user, workspace = await _register_and_workspace(client, register_user)
    response = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/documents",
        headers=_auth(user["access_token"]),
        files={"file": ("big.pdf", b"x" * 1024, "application/pdf")},
    )
    assert response.status_code == 413


async def test_non_member_cannot_upload(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_workspace = await _register_and_workspace(client, register_user)
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    response = await client.post(
        f"/api/v1/workspaces/{alice_workspace['id']}/documents",
        headers=_auth(bob["access_token"]),
        files={"file": ("handbook.pdf", _make_pdf(), "application/pdf")},
    )
    assert response.status_code == 403


async def test_delete_document(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    doc = await _upload(client, user["access_token"], workspace["id"])
    await ingest_document(db_session, uuid.UUID(doc["id"]))

    response = await client.delete(
        f"/api/v1/documents/{doc['id']}",
        headers=_auth(user["access_token"]),
    )
    assert response.status_code == 204

    gone = await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(user["access_token"]))
    assert gone.status_code == 404

    remaining = await db_session.scalar(
        select(func.count()).select_from(Document).where(Document.id == uuid.UUID(doc["id"]))
    )
    assert remaining == 0


async def test_delete_document_requires_membership(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_workspace = await _register_and_workspace(client, register_user)
    doc = await _upload(client, alice["access_token"], alice_workspace["id"])
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    response = await client.delete(
        f"/api/v1/documents/{doc['id']}",
        headers=_auth(bob["access_token"]),
    )
    assert response.status_code == 403


async def test_ingest_marks_failed_on_garbage_pdf(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    doc = await _upload(
        client,
        user["access_token"],
        workspace["id"],
        name="broken.pdf",
        content=b"not a real pdf at all",
    )
    await ingest_document(db_session, uuid.UUID(doc["id"]))
    updated = (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(user["access_token"]))).json()
    assert updated["status"] == "failed"
    assert updated["error_message"]
