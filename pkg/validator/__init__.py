"""
Reusable input validation helpers.

Equivalent of pkg/validator/ in the standard Go layout.

Provides lightweight, framework-agnostic validators that can be used
by any layer (service, repository, handler) without importing Pydantic
or FastAPI directly.

Usage:
    from pkg.validator import validate_not_blank, validate_one_of

    validate_not_blank("language", value)
    validate_one_of("theme", value, {"light", "dark"})
"""

from __future__ import annotations

from typing import Any, Set

from pkg.errors import ValidationError


def validate_not_blank(field: str, value: Any) -> None:
    """Raise ValidationError if *value* is None or an empty/whitespace string.

    Args:
        field: Human-readable field name used in the error message.
        value: The value to test.

    Raises:
        ValidationError: if *value* is blank.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(field=field, reason="must not be blank")


def validate_one_of(field: str, value: Any, allowed: Set[Any]) -> None:
    """Raise ValidationError if *value* is not in *allowed*.

    Args:
        field:   Human-readable field name used in the error message.
        value:   The value to test.
        allowed: Set of permitted values.

    Raises:
        ValidationError: if *value* is not in *allowed*.
    """
    if value not in allowed:
        raise ValidationError(
            field=field,
            reason=f"must be one of {sorted(str(a) for a in allowed)}",
        )


def validate_min_length(field: str, value: str, min_length: int) -> None:
    """Raise ValidationError if *value* is shorter than *min_length*.

    Args:
        field:      Human-readable field name.
        value:      The string to test.
        min_length: Minimum acceptable length (inclusive).

    Raises:
        ValidationError: if ``len(value) < min_length``.
    """
    if len(value) < min_length:
        raise ValidationError(
            field=field,
            reason=f"must be at least {min_length} characters long",
        )
