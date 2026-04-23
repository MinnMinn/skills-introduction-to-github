"""
HTTP middleware — authentication / authorisation.

Equivalent of internal/middleware/auth.go in the standard Go layout.

This module provides a FastAPI middleware stub for bearer-token
authentication.  In this initial scaffold the token check is a no-op
(pass-through) so that the application runs without configuration;
replace ``_verify_token`` with a real JWT/OAuth2 validation in production.

Usage (wire into the app in cmd/api/main.py):

    from internal.middleware.auth import AuthMiddleware
    app.add_middleware(AuthMiddleware)
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Paths that do not require authentication
_PUBLIC_PATHS: frozenset[str] = frozenset({"/health", "/docs", "/openapi.json"})


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates the Authorization: Bearer <token> header on protected routes.

    In production, replace the ``_verify_token`` stub with real token
    introspection (e.g. python-jose for JWT, or an OAuth2 token endpoint).
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # ----------------------------------------------------------------
        # TODO: replace stub with real token verification
        # token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        # if not _verify_token(token):
        #     return Response(status_code=401, content="Unauthorized")
        # ----------------------------------------------------------------

        return await call_next(request)


def _verify_token(token: str) -> bool:  # pragma: no cover
    """Stub — always returns True until real auth is wired in."""
    return bool(token)
