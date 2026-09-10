class AppError(Exception):
    """Base class for domain-level errors raised by services."""


class UnsupportedFileTypeError(AppError):
    """Raised when a document's extension is not among the allowed formats."""


class DuplicateEmailError(AppError):
    """Raised when registering an email that already exists."""


class DuplicateNameError(AppError):
    """Raised when creating a resource whose name already exists in scope."""


class InvalidReferenceError(AppError):
    """Raised when referencing a resource that does not exist or is not accessible."""


class StoredFileMissingError(AppError):
    """Raised when the stored object for a document cannot be found."""


class QueueUnavailableError(AppError):
    """Raised when a background job cannot be scheduled."""


class QuotaExceededError(AppError):
    """Raised when a workspace hits its document-count or storage cap."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class InvalidInviteCodeError(AppError):
    """Raised when a workspace invite code is invalid or not found."""
