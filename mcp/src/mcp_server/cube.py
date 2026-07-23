"""Thin client for the Cube REST API.

Wraps the three endpoints the MCP server needs: ``/meta`` (schema), ``/load``
(run a query), and ``/sql`` (compile a query to SQL without running it). Each
request carries a freshly signed short-lived JWT so Cube can verify it against
the shared API secret.
"""

import httpx

from mcp_server.auth import sign_cube_token

API_PREFIX = "/cubejs-api/v1"


class CubeError(RuntimeError):
    """Raised when Cube returns an error response."""


class CubeClient:
    def __init__(self, base_url: str, api_secret: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._api_secret = api_secret
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {sign_cube_token(self._api_secret)}"}

    def _url(self, path: str) -> str:
        return f"{self._base_url}{API_PREFIX}{path}"

    def meta(self) -> dict:
        resp = httpx.get(self._url("/meta"), headers=self._headers(), timeout=self._timeout)
        return self._json_or_raise(resp)

    def load(self, query: dict) -> list[dict]:
        resp = httpx.post(
            self._url("/load"), json={"query": query}, headers=self._headers(), timeout=self._timeout
        )
        return self._json_or_raise(resp).get("data", [])

    def sql(self, query: dict) -> str:
        resp = httpx.post(
            self._url("/sql"), json={"query": query}, headers=self._headers(), timeout=self._timeout
        )
        payload = self._json_or_raise(resp)
        return payload.get("sql", {}).get("sql", ["", []])[0]

    @staticmethod
    def _json_or_raise(resp: httpx.Response) -> dict:
        try:
            payload = resp.json()
        except ValueError:
            payload = {}
        if resp.status_code >= 400 or "error" in payload:
            message = payload.get("error", resp.text or f"HTTP {resp.status_code}")
            raise CubeError(str(message))
        return payload
