"""Custom exceptions for the Lasoo integration."""


class LasooError(Exception):
    """Raised for expected, user-facing errors. Mapped to a clean HTTP response."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
