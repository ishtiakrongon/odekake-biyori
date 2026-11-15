class ExternalServiceError(Exception):
    """Raised when a public API fails or returns data we cannot use."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code