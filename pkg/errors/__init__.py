"""
Reusable application-level error types.

Equivalent of pkg/errors/ in the standard Go layout.

Defines a small hierarchy of typed exceptions so that different layers
can raise meaningful errors that the handler layer translates into the
correct HTTP status codes without importing framework code.

Usage:
    from pkg.errors import NotFoundError, ValidationError

    raise NotFoundError(resource="user", identifier="u-99")
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application-defined errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class NotFoundError(AppError):
    """Raised when a requested resource does not exist.

    Corresponds to HTTP 404 in the handler layer.
    """

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(f"{resource} '{identifier}' not found")
        self.resource = resource
        self.identifier = identifier


class ValidationError(AppError):
    """Raised when input fails business-rule validation.

    Corresponds to HTTP 422 in the handler layer.
    """

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"Validation failed for '{field}': {reason}")
        self.field = field
        self.reason = reason


class ConflictError(AppError):
    """Raised when an operation would create a duplicate resource.

    Corresponds to HTTP 409 in the handler layer.
    """
