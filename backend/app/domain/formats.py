from pathlib import Path

EXTENSION_TO_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "md": "text/markdown",
}

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(EXTENSION_TO_MIME)


def mime_for(filename: str) -> str:
    ext = Path(filename).suffix.lstrip(".").lower()
    return EXTENSION_TO_MIME[ext]


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lstrip(".").lower() in ALLOWED_EXTENSIONS
