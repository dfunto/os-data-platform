"""Tool logic shared by the MCP tools.

Every data-touching call fetches the current governed schema from Cube, then
validates the requested query against it before anything runs. This is the
fail-closed guarantee: an unmodelled member raises before ``load``/``sql`` is
ever called, so the agent can never reach ClickHouse outside the model.

The functions take any object exposing ``meta``/``load``/``sql`` (the
``CubeClient``), which keeps them testable without HTTP.
"""

from typing import Protocol

from mcp_server.schema import parse_meta, validate_query


class Cube(Protocol):
    def meta(self) -> dict: ...
    def load(self, query: dict) -> list[dict]: ...
    def sql(self, query: dict) -> str: ...


def describe_schema(client: Cube) -> dict:
    """Return the governed vocabulary: cubes with their measures and dimensions."""
    schema = parse_meta(client.meta())
    return {
        "cubes": [
            {
                "name": cube.name,
                "title": cube.title,
                "measures": [_member(m) for m in cube.measures],
                "dimensions": [_member(d) for d in cube.dimensions],
            }
            for cube in schema.cubes
        ]
    }


def run_query(client: Cube, query: dict) -> list[dict]:
    """Validate against the model, then run the query and return rows."""
    schema = parse_meta(client.meta())
    validate_query(query, schema)
    return client.load(query)


def preview_sql(client: Cube, query: dict) -> str:
    """Validate against the model, then return the compiled SQL without running it."""
    schema = parse_meta(client.meta())
    validate_query(query, schema)
    return client.sql(query)


def _member(m) -> dict:
    out = {"name": m.name, "type": m.type}
    if m.title:
        out["title"] = m.title
    if m.description:
        out["description"] = m.description
    return out
