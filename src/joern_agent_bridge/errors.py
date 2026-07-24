"""Domain exceptions with stable error codes."""

from __future__ import annotations

from typing import Any


class BridgeError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable


class PathViolation(BridgeError):
    pass


class JoernUnavailable(BridgeError):
    pass


class JoernExecutionError(BridgeError):
    pass
