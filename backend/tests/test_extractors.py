from io import BytesIO
from pathlib import Path

import fitz
from docx import Document as DocxDocument

from app.services.ingestion.extractors import get_extractor
from app.services.ingestion.extractors.base import UnsupportedFormatError


def _write(tmp: Path, name: str, data: bytes) -> Path:
    path = tmp / name
    path.write_bytes(data)
    return path


def _make_pdf() -> bytes:
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Employee Handbook Page One", fontsize=12)
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Employees receive 25 vacation days per year", fontsize=12)
    return doc.tobytes()


def _make_docx() -> bytes:
    buffer = BytesIO()
    doc = DocxDocument()
    doc.add_paragraph("Standard payment terms are net 30 days from invoice.")
    doc.save(buffer)
    return buffer.getvalue()


async def test_pdf_extractor_returns_pages(tmp_path: Path) -> None:
    path = _write(tmp_path, "handbook.pdf", _make_pdf())
    pages = get_extractor("application/pdf").extract(path)
    assert [p.page_number for p in pages] == [1, 2]
    assert "Page One" in pages[0].content
    assert "vacation days" in pages[1].content


async def test_docx_extractor_single_logical_page(tmp_path: Path) -> None:
    path = _write(tmp_path, "contract.docx", _make_docx())
    pages = get_extractor("application/vnd.openxmlformats-officedocument.wordprocessingml.document").extract(path)
    assert [p.page_number for p in pages] == [1]
    assert "net 30 days" in pages[0].content


async def test_text_extractor(tmp_path: Path) -> None:
    path = _write(tmp_path, "notes.md", b"# Notes\n\nSome internal notes.")
    pages = get_extractor("text/markdown").extract(path)
    assert [p.page_number for p in pages] == [1]
    assert "internal notes" in pages[0].content


async def test_get_extractor_unsupported_raises() -> None:
    import pytest

    with pytest.raises(UnsupportedFormatError):
        get_extractor("application/x-rar")
