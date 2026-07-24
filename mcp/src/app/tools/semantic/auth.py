"""Cube authentication: sign short-lived JWTs with the Cube API secret.

Cube verifies the Authorization bearer token against ``CUBEJS_API_SECRET``
(HS256). The MCP server holds no user identity; it signs a minimal, short-lived
token per request so the secret is the only shared material with Cube.
"""

import time

import jwt as pyjwt

DEFAULT_EXPIRY_SECONDS = 300


def sign_cube_token(secret: str, expires_in_seconds: int = DEFAULT_EXPIRY_SECONDS) -> str:
    """Return an HS256 JWT signed with ``secret``, expiring in the given window."""
    now = int(time.time())
    payload = {"iat": now, "exp": now + expires_in_seconds}
    return pyjwt.encode(payload, secret, algorithm="HS256")