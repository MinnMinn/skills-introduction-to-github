"""JWT authentication utilities."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _credentials_exception(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT, returning its payload.

    Raises HTTPException 401 on any validation failure.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except ExpiredSignatureError:
        raise _credentials_exception("Token has expired")
    except JWTError:
        raise _credentials_exception("Invalid token")


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency — extract and validate the Bearer JWT, return user_id."""
    if credentials is None:
        raise _credentials_exception("Authorization header missing")

    payload = decode_token(credentials.credentials)

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise _credentials_exception("Token missing 'sub' claim")

    return user_id
