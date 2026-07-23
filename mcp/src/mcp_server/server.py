"""FastMCP server exposing the governed semantic layer.

Tools are thin wrappers over :mod:`mcp_server.service`, which validates every
query against Cube's model and fails closed on anything unmodelled. Transport is
chosen by ``MCP_TRANSPORT`` (``stdio`` for local agents like Claude Code,
``streamable-http`` for the deployed service).
"""

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server import service
from mcp_server.config import Config
from mcp_server.cube import CubeClient


def build_server() -> FastMCP:
    config = Config.from_env()
    client = CubeClient(base_url=config.cube_url, api_secret=config.api_secret)

    mcp = FastMCP(
        "os-data-platform",
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8000")),
    )

    @mcp.tool()
    def describe_schema() -> dict:
        """List the governed cubes with their measures and dimensions.

        Call this first to discover what can be queried. Only members returned
        here are valid; anything else is rejected before it reaches the warehouse.
        """
        return service.describe_schema(client)

    @mcp.tool()
    def query(
        measures: list[str] | None = None,
        dimensions: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        time_dimensions: list[dict[str, Any]] | None = None,
        order: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Run a governed query over the semantic layer and return rows.

        Members must be fully-qualified (e.g. ``noaa_ghcn_stations.count``) and
        come from ``describe_schema``. The query is validated against the model
        before running, so unmodelled members fail closed and never hit SQL.
        """
        return service.run_query(client, _cube_query(measures, dimensions, filters, time_dimensions, order, limit))

    @mcp.tool()
    def preview_sql(
        measures: list[str] | None = None,
        dimensions: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        time_dimensions: list[dict[str, Any]] | None = None,
        order: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> str:
        """Return the SQL a query would compile to, without running it."""
        return service.preview_sql(client, _cube_query(measures, dimensions, filters, time_dimensions, order, limit))

    return mcp


def _cube_query(measures, dimensions, filters, time_dimensions, order, limit) -> dict:
    query: dict[str, Any] = {}
    if measures:
        query["measures"] = measures
    if dimensions:
        query["dimensions"] = dimensions
    if filters:
        query["filters"] = filters
    if time_dimensions:
        query["timeDimensions"] = time_dimensions
    if order:
        query["order"] = order
    if limit is not None:
        query["limit"] = limit
    return query


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    build_server().run(transport=transport)


if __name__ == "__main__":
    main()
