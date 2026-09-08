from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

import anyio

from app.core.config import get_settings


class StorageError(Exception):
    """Raised when a storage operation fails."""


class TooLargeError(StorageError):
    """Raised when a file exceeds the configured upload limit."""


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, source: BinaryIO, max_size: int | None = None) -> int:
        """Persist the stream under ``key`` and return the number of bytes written."""

    @abstractmethod
    async def open(self, key: str) -> Path:
        """Return a local path to the stored object."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove the stored object if it exists."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return True if the object exists."""

    @abstractmethod
    async def clear_all(self) -> None:
        """Remove every stored object."""


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or Path(get_settings().storage_dir)).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.base_dir / key

    def _save_sync(self, key: str, source: BinaryIO, max_size: int | None) -> int:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with target.open("wb") as out:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if max_size is not None and size > max_size:
                    raise TooLargeError(f"File exceeds limit of {max_size} bytes")
                out.write(chunk)
        return size

    def _open_sync(self, key: str) -> Path:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path

    def _delete_sync(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    async def save(self, key: str, source: BinaryIO, max_size: int | None = None) -> int:
        return await anyio.to_thread.run_sync(self._save_sync, key, source, max_size)

    async def open(self, key: str) -> Path:
        return await anyio.to_thread.run_sync(self._open_sync, key)

    async def delete(self, key: str) -> None:
        await anyio.to_thread.run_sync(self._delete_sync, key)

    async def exists(self, key: str) -> bool:
        return await anyio.to_thread.run_sync(lambda: self._path(key).is_file())

    async def clear_all(self) -> None:
        await anyio.to_thread.run_sync(self._clear_all_sync)

    def _clear_all_sync(self) -> None:
        if not self.base_dir.is_dir():
            return
        for path in self.base_dir.rglob("*"):
            if path.is_file():
                path.unlink()
        for path in sorted(self.base_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass


@lru_cache
def get_storage() -> StorageBackend:
    return LocalStorage()
