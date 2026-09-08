from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    DuplicateEmailError,
    DuplicateNameError,
    InvalidReferenceError,
    QueueUnavailableError,
    QuotaExceededError,
    StoredFileMissingError,
    UnsupportedFileTypeError,
)
from app.infrastructure.storage import TooLargeError


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(QuotaExceededError)
    async def _quota_exceeded(_request: Request, exc: QuotaExceededError) -> JSONResponse:
        return _error(status.HTTP_413_CONTENT_TOO_LARGE, exc.code)

    @app.exception_handler(UnsupportedFileTypeError)
    async def _unsupported(_request: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
        return _error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc))

    @app.exception_handler(TooLargeError)
    async def _too_large(_request: Request, exc: TooLargeError) -> JSONResponse:
        return _error(status.HTTP_413_CONTENT_TOO_LARGE, str(exc))

    @app.exception_handler(DuplicateEmailError)
    async def _duplicate_email(_request: Request, exc: DuplicateEmailError) -> JSONResponse:
        return _error(status.HTTP_409_CONFLICT, str(exc))

    @app.exception_handler(DuplicateNameError)
    async def _duplicate_name(_request: Request, exc: DuplicateNameError) -> JSONResponse:
        return _error(status.HTTP_409_CONFLICT, str(exc))

    @app.exception_handler(InvalidReferenceError)
    async def _invalid_reference(_request: Request, exc: InvalidReferenceError) -> JSONResponse:
        return _error(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.exception_handler(StoredFileMissingError)
    async def _file_missing(_request: Request, exc: StoredFileMissingError) -> JSONResponse:
        return _error(status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(QueueUnavailableError)
    async def _queue_unavailable(_request: Request, exc: QueueUnavailableError) -> JSONResponse:
        return _error(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
