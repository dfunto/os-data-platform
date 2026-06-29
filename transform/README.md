# Transform

SQLMesh project for data transformations. Reads from `raw` tables in ClickHouse and produces `cleansed` and `curated` layers.

## Architecture

- **Engine**: ClickHouse (execution + storage)
- **State backend**: PostgreSQL (SQLMesh metadata)
- **Dialect**: ClickHouse SQL
- **Orchestration**: Integrated into Dagster via `dagster-sqlmesh` (see `orchestrator/src/assets/transform.py`)

## Models

```
models/
  cleansed/
    noaa_ghcn_countries.sql     # FULL refresh, grain: id
    noaa_ghcn_states.sql        # FULL refresh, grain: id
    noaa_ghcn_stations.sql      # FULL refresh, grain: id
    noaa_ghcn_inventory.sql     # FULL refresh, grain: id
```

All cleansed models read from `raw.*` tables created by the ingestion pipeline.

## Configuration

Connection config in `config.yaml`. Hosts are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLMESH_CLICKHOUSE_HOST` | `localhost` | ClickHouse HTTP endpoint |
| `SQLMESH_POSTGRES_HOST` | `localhost` | PostgreSQL state backend |
| `OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD` | (required) | PostgreSQL password for `platform` user |

For local development, port-forward the K8s services and use `localhost`. Inside Docker, set hosts to `host.docker.internal`.

## Standalone Usage

```shell
# Install dependencies
uv sync

# Plan changes (preview what will run)
uv run sqlmesh plan

# Apply to prod environment
uv run sqlmesh plan prod

# Run pending backfills
uv run sqlmesh run
```

## Dagster Integration

Transform assets are registered in Dagster via `dagster-sqlmesh`. The integration:

- Auto-discovers SQLMesh models and registers them as Dagster assets
- Links cleansed assets to raw ingestion assets via a custom `SQLMeshDagsterTranslator`
- Runs `sqlmesh plan + run` against the `prod` environment on each materialization
- Uses `SQLMeshResource` from `dagster-sqlmesh`

## Adding New Models

1. Create a `.sql` file under `models/<layer>/` (e.g., `models/cleansed/my_model.sql`)
2. Define the `MODEL` block with `name`, `kind`, and `grain`
3. Write a `SELECT` query reading from upstream tables
4. Run `sqlmesh plan` to preview and apply

Example:

```sql
MODEL (
  name cleansed.my_table,
  kind FULL,
  grain id
);

SELECT
  TRIM(col) as id,
  col2
FROM raw.my_source_table
```