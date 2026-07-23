# MCP server

Governed [MCP](https://modelcontextprotocol.io) server over the semantic (Cube) layer.
Any MCP-capable agent (Claude Code, Claude Desktop, Cursor) connects and asks questions about the data in natural language.
The agent can only query through Cube's modelled measures and dimensions; anything unmodelled is rejected before it reaches ClickHouse, so answers stay correct by construction.

This is the platform's single MCP server.
The pilot ships the read-only semantic-query tools (capability 4 in [ROADMAP.md](../ROADMAP.md)); authoring tools for ingestion, transform, and semantic models are added here later.

## Tools

| Tool | Purpose |
|------|---------|
| `describe_schema` | List the governed cubes, measures, and dimensions. Call first to discover what is queryable. |
| `query` | Run a governed Cube query (measures, dimensions, filters, time dimensions, order, limit) and return rows. |
| `preview_sql` | Show the SQL a query compiles to, without running it. |

Every tool validates the request against the live Cube model and fails closed on any unmodelled member.

## Layout

```
src/mcp_server/
  config.py    env config (CUBE_URL, CUBEJS_API_SECRET)
  auth.py      signs short-lived Cube JWTs
  cube.py      CubeClient: /meta, /load, /sql
  schema.py    parse /meta + validate_query (fail closed)
  service.py   tool logic (validate then run)
  server.py    FastMCP app + transport
tests/         unit (schema, cube, jwt, service, server) + integration (live Cube)
```

## Prerequisites

Cube must be reachable. From the repo root:

```shell
make forward   # port-forward ClickHouse from Kubernetes
make cube      # start the Cube semantic layer on :4000
```

## Use with local Claude Code (stdio)

```shell
claude mcp add os-data-platform-semantic \
  --env CUBE_URL=http://localhost:4000 \
  --env CUBEJS_API_SECRET=dev-secret \
  -- uv --directory "$(pwd)/mcp" run mcp-server
```

Then in a Claude Code session, ask e.g. "which countries have the most weather stations?".
Verify the connection with `claude mcp list`.

## Run as an HTTP service (deploy parity)

```shell
docker compose up --build   # serves Streamable HTTP on :8000
```

Kubernetes deployment is in [`helm/mcp`](../helm/mcp).

## Tests

```shell
uv run --extra dev pytest                    # unit tests
uv run --extra dev pytest -m integration     # against a live Cube (needs make forward + make cube)
```
