"""Per-user rate limiting.

Each submission costs real OpenAI credit, so the limit is keyed on the
authenticated user where possible and falls back to the client IP.
"""

from __future__ import annotations

import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def _identify(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        try:
            payload = jwt.decode(
                header[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            return f"user:{payload['sub']}"
        except (jwt.PyJWTError, KeyError):
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_identify, default_limits=[])
