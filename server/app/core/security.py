from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def verify_bearer_token(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {get_settings().api_token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token.",
        )
