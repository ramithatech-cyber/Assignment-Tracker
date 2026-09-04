"""Errors that carry a message safe to show a student verbatim."""


class AnalysisError(Exception):
    """Something went wrong that the submitter can understand and act on."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
