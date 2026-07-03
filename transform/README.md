# Transform (dbt)

dbt project for data transformations. Reads from `raw` tables in ClickHouse and produces the
`cleansed` layer.

## Architecture

- **Engine**: ClickHouse (execution + storage), adapter `dbt-clickhouse`
- **Dialect**: ClickHouse SQL
- **State**: none — dbt is stateless. Partition/backfill tracking is owned by Dagster
  (`dagster-dbt`), not by the transform layer.
- **Orchestration**: Dagster via `dagster-dbt` (see `orchestrator/src/assets/transform.py`)

## Layout

```
models/
  sources.yml                 # raw.* external tables produced by ingestion
  cleansed/noaa_ghcn/         # cleansed models (files prefixed noaa_ghcn_*)
    *_countries.sql  *_states.sql  *_stations.sql  *_inventory.sql   # table
    *_measurement_flags_cleansed.sql  *_quality_flags_cleansed.sql  *_source_flags_cleansed.sql  # view (over seeds)
    *_observations.sql                                               # incremental, insert_overwrite by year
seeds/noaa_ghcn/              # flag lookup CSVs -> raw schema
macros/generate_schema_name.sql  # use schema (raw/cleansed) verbatim
```

## Model kinds

| Model | Materialization |
|-------|-----------------|
| countries / states / stations / inventory | `table` |
| measurement_flags / quality_flags / source_flags | `view` (over seeds) |
| observations | `incremental`, `insert_overwrite`, `partition_by=observation_year` |

## Configuration

Connection in `profiles.yml`, env-var driven:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLICKHOUSE_ENDPOINT_URL` | `localhost` | ClickHouse HTTP host |
| `CLICKHOUSE_HTTP_PORT` | `8123` | ClickHouse HTTP port |
| `CLICKHOUSE_PASSWORD` | (empty) | password for `default` user |

## Standalone usage

```shell
uv sync
uv run dbt seed                                  # load flag CSVs into raw
uv run dbt run --exclude noaa_ghcn_observations  # table + view models
# incremental model — one partition (year) per invocation, driven by vars:
uv run dbt run --select noaa_ghcn_observations \
  --vars '{start_ds: "2024-01-01", end_ds: "2024-12-31"}'
```

## Incremental / partitions

`observations` is `incremental` with `incremental_strategy='insert_overwrite'` and
`partition_by='observation_year'`. Each run replaces only the partitions present in the incoming
data. The processed window is scoped by `var('start_ds')` / `var('end_ds')` inside `is_incremental()`.
Dagster passes those vars from the partition key of the yearly-partitioned asset, giving
per-partition tracking and backfills in the Dagster UI.
