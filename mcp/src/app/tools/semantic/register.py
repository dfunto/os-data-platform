"""Semantic-layer capability: governed query + introspection over Cube.

One capability, one backend: this module owns the :class:`CubeClient` and every
tool that speaks to it. Tools delegate to ``service``, which validates against
Cube's model and fails closed on anything unmodelled.
"""

from mcp.server.fastmcp import FastMCP

from app.config import Config
from app.tools.semantic import service
from app.tools.semantic.client import CubeClient
from app.tools.semantic.models import CubeQuery


def register(mcp: FastMCP, config: Config) -> None:
    client = CubeClient(base_url=config.cube_url, api_secret=config.api_secret)

    @mcp.tool()
    def describe_schema() -> dict:
        """List the governed cubes with their measures and dimensions.

        Call this first to discover what can be queried. Only members returned
        here are valid; anything else is rejected before it reaches the warehouse.
        """
        return service.describe_schema(client)

    @mcp.tool()
    def query(q: CubeQuery) -> list[dict]:
        """Run a governed query over the semantic layer and return rows.

        Members must be fully-qualified (e.g. ``noaa_ghcn_stations.count``) and
        come from ``describe_schema``. The query is validated against the model
        before running, so unmodelled members fail closed and never hit SQL.
        """
        return service.run_query(client, q.to_cube())

    @mcp.tool()
    def preview_sql(q: CubeQuery) -> str:
        """Return the SQL a query would compile to, without running it."""
        return service.preview_sql(client, q.to_cube())
