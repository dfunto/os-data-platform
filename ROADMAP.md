# Roadmap

This roadmap describes the next major direction for the platform: exposing every layer to AI agents through governed interfaces.

## Vision

Users should be able to operate the whole platform by prompting AI agents, without any agent inventing new mechanisms.
The platform does not build its own agent or chat product.
Instead it exposes **governed interfaces that existing agents (Claude Desktop, Cursor, or a user's own agent) plug into**.
Each interface constrains what an agent can do so that correctness and safety are guaranteed by the platform, not by the LLM.

The standard for "existing agents plug in" is the **Model Context Protocol (MCP)**.
Each platform layer gets its own MCP server that exposes a small set of tools bounded to that layer's existing capabilities.

## Target capabilities

Four AI-agent capabilities, one per existing layer.
Each is its own spec, plan, and build cycle.

| # | Capability | Agent writes / touches | Guardrail |
|---|------------|------------------------|-----------|
| 1 | Add ingestion source by prompt | `configuration/ingestion/*.yml` | Only existing `source_type` values (`s3`, `api`). Agent never writes new pipeline code. |
| 2 | Add transformation by prompt | `transform/models/**/*.sql` (dbt) | Must be valid dbt against existing sources. |
| 3 | Add semantic model by prompt | `semantic/model/cubes/*` | Must be a valid Cube model over `curated`. |
| 4 | Ask questions in natural language | Queries the semantic layer (read-only) | Every query compiles through Cube's governed model and fails closed on anything unmodelled. |

## Shared architecture decisions

These decisions apply across all four capabilities.

**Interface is MCP, not a bespoke agent or chat.**
The platform ships MCP servers.
The agent is bring-your-own.
The MCP server enforces the contract of its layer.

**Trust and apply model: start human-in-the-loop, evolve to auto-apply.**
For the mutating capabilities (1 to 3), the agent proposes an artifact, the platform validates it, a human reviews and merges, and existing CI and Dagster deploy it.
Validation and apply are kept as separate steps so that moving to auto-apply later only swaps the apply step, not the validation.
The read-only capability (4) needs no apply step.

**One MCP server per layer, same pattern, different artifact.**
The validate-then-apply loop is identical across capabilities; only the artifact and its validator differ.
The shared foundation is extracted from the first working server rather than designed up front.

**Language and runtime: Python 3.12 with FastMCP.**
This reuses the `orchestrator/` toolchain and can later share the in-tree `common` config models.
Servers talk to their backing service (Cube, dbt, ClickHouse) over HTTP or the local filesystem.

**Deployment: same shape as the `semantic/` layer.**
Each MCP server is its own top-level directory with a `Dockerfile`, a `docker-compose.yml` for local development, and a chart under `helm/`.
Transport is Streamable HTTP so the server runs always-on as a service.
Development runs via docker-compose; integration tests deploy to Kubernetes via Helm against the live platform.

## Sequencing

Capability 4 is the pilot and is built first.
It is read-only, so it carries no mutation or apply risk.
The `curated` schema and the `semantic/` Cube model already exist, so it delivers visible value immediately.
It is the clearest expression of the correctness story, since Cube fails closed.
Building it first lets the shared MCP foundation be extracted from a real, working server before it is pointed at mutations.

Capabilities 1 to 3 (the authoring agents) follow, reusing the pilot's foundation and adding the validate-then-apply harness.

## Pilot: semantic-layer MCP server (capability 4)

**Purpose.**
A governed MCP interface so any bring-your-own agent can ask natural-language questions and get correct answers.
The only way to touch data is through Cube's modelled measures and dimensions.
The agent cannot emit raw SQL, cannot reach `curated` tables directly, and cannot query anything unmodelled.
Cube failing closed is the correctness guarantee.

Scope is natural-language question and answer only.
There is no dashboard persistence and no layout, which are deferred to a later spec.

**Component.**
A new top-level directory `semantic-mcp/` mirroring the shape of `semantic/`.
Python 3.12 plus FastMCP, Streamable HTTP transport.
It is a thin, stateless proxy that holds no data and forwards to the Cube REST API.
It signs a short-lived JWT with `CUBEJS_API_SECRET` and calls Cube on port 4000.

**Tools exposed.**

| Tool | Does | Backed by |
|------|------|-----------|
| `describe_schema` | Lists cubes, measures, dimensions, their types and descriptions. | Cube `/meta` |
| `query` | Runs one Cube query (measures, dimensions, filters, time dimensions, limit) and returns rows. | Cube `/load` |
| `preview_sql` | Optional. Shows the compiled SQL for a query without running it. | Cube `/sql` |

The `query` tool takes a structured Cube query, not a SQL string.
It is validated against `/meta` before being sent.
An unknown member returns an error to the agent and never reaches ClickHouse.

**Flow.**

```
BYO agent -> MCP describe_schema      # sees governed vocabulary
          -> MCP query(measures=[...], dimensions=[...])
          -> server signs JWT -> Cube /load -> ClickHouse curated (read-only)
          -> rows back -> agent phrases the natural-language answer
```

**Repository and deployment.**

```
semantic-mcp/
  src/                 FastMCP server, Cube client, JWT signer, query models
  tests/               unit (schema, query, JWT) + integration (live Cube)
  Dockerfile           python:3.12-slim + FastMCP
  docker-compose.yml   dev; depends on the semantic cube; host-gateway to ClickHouse
  pyproject.toml
helm/semantic-mcp/     Deployment + Service (HTTP), env from the Cube secret
```

Image: `dadutra2/os-data-platform-semantic-mcp:latest`.
Development runs via docker-compose alongside `semantic/`.
Integration testing deploys via Helm to the `os-data-platform` namespace against live Cube and ClickHouse.

**Testing.**
Unit tests cover JWT signing, `/meta` parsing, and query validation rejecting an unmodelled member.
Integration tests on Kubernetes assert that `describe_schema` returns the three existing cubes, that a real `query` (for example station count by country) returns rows, and that a bad query fails closed.

## Prior roadmap

These items were the original roadmap (previously listed in the README).
They remain possible future work but are lower priority than the agent-interface direction above.

- Ingest API data (done)
- Ingest CDC data
- Ingest realtime data
- Realtime data transformation
- Realtime dashboard
- Machine learning capability