from app.services.ingestion.chunker import chunk_pages, chunk_text
from app.services.ingestion.extractors.base import ExtractedPage


def test_chunk_text_long_text_respects_size():
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(text, chunk_size=800, overlap=120)
    assert chunks
    assert all(len(c.split()) <= 800 for c in chunks)


def test_chunk_text_short_text_single_chunk():
    assert chunk_text("hello world") == ["hello world"]


def test_chunk_text_empty():
    assert chunk_text("   ") == []
    assert chunk_text("") == []


def test_chunk_text_overlap_shares_words():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 2
    first_tail = set(chunks[0].split()[-50:])
    second_head = set(chunks[1].split()[:50])
    assert first_tail & second_head


def test_chunk_pages_preserves_page_number_and_order():
    pages = [
        ExtractedPage(page_number=1, content=" ".join(f"a{i}" for i in range(300))),
        ExtractedPage(page_number=2, content=" ".join(f"b{i}" for i in range(300))),
    ]
    chunks = chunk_pages(pages, chunk_size=200, overlap=20)
    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(0 <= c.token_count <= 200 for c in chunks)


def test_chunk_pages_no_chunk_spans_pages():
    pages = [
        ExtractedPage(page_number=1, content=" ".join(f"a{i}" for i in range(100))),
        ExtractedPage(page_number=2, content=" ".join(f"b{i}" for i in range(100))),
    ]
    chunks = chunk_pages(pages, chunk_size=200, overlap=0)
    assert all(c.page_number in (1, 2) for c in chunks)
    assert all("b" not in c.content.split() or c.page_number == 2 for c in chunks)
