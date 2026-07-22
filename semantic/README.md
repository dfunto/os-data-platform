# Semantic Layer (Cube Core)

Governed query layer over the `curated` ClickHouse schema.
An English-to-SQL agent selects governed measures and dimensions instead of writing raw SQL, so business definitions (units, filters, two-stage averaging) can never be violated.

Cube compiles governed queries to ClickHouse SQL and fails closed on anything not modelled.
See `docs/superpowers/specs/2026-07-20-semantic-layer-cube-design.md`.

## Model

`model/cubes/` defines three cubes over the curated facts:

- `station_year` - governed climate metrics (per-country / global averages; cross-station second stage of the two-stage averages).
- `stations` - station coverage and mean geography per country.
- `observations` - observation-grain detail (normalized value, filter by `measure` / `quality_flag`).

## Local development

1. From the repo root, forward the cluster services (ClickHouse must be reachable on `localhost:8123`):

   ```shell
   make forward
   ```

2. Start Cube:

   ```shell
   cp .env.example .env
   docker compose up
   ```

3. Open the dev playground at http://localhost:4000 to browse cubes and build queries.

4. Query through the SQL API (Postgres wire protocol on port 15432):

   ```shell
   psql "host=localhost port=15432 user=cube password=cube dbname=cube" \
     -c "SELECT MEASURE(avg_tmax_celsius) AS avg_tmax, country_name
         FROM station_year WHERE observation_year = 2024 GROUP BY country_name"
   ```

   This returns per-country average maximum temperature in °C, matching
   `reporting.noaa_ghcn_avg_yearly_observations_per_country`.

## Deployment

Deployed to Kubernetes via the `helm/semantic` chart (api-only; no Cube Store).
See `helm/README.md`.
