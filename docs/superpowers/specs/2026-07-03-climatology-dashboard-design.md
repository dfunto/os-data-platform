# Global Historical Climatology Network Dashboard — Design

Date: 2026-07-03

## Goal

Build a full-fledged Superset dashboard, "Global Historical Climatology Network",
backed entirely by dbt **curated** models. Superset is the presentation layer only:
no joins, no business logic, no ad-hoc SQL datasets. All aggregation lives in dbt.

## Data context (from ClickHouse `cleansed` / `curated`)

- Observations span `observation_year` **2024–2026** (3 years), ~174M rows.
- Measures present: PRCP, SNOW, TMAX, TMIN, SNWD, TAVG, TOBS, WESD, ... .
- 132,501 stations across 219 countries.
- Raw temperature/precip/snow values are in tenths (÷10 → °C / mm), matching the
  existing curated model convention.
- Only `quality_flag IS NULL` rows pass GHCN QC and are kept.
- Temperature aggregation is **two-stage** (average per station first, then across
  stations) so station-dense countries don't dominate — established in
  `noaa_ghcn_avg_yearly_observations_per_country`.

## Curated dbt models (`transform/models/curated/`)

Materialized as tables in `curated` schema (per `dbt_project.yml`).

### Reused
- **`noaa_ghcn_avg_yearly_observations_per_country`** (exists): per country-year —
  `station_count, avg_tmax_celsius, avg_tmin_celsius, avg_yearly_precip_mm`.
  Feeds the world map and the top-precipitation bar.

### New
1. **`noaa_ghcn_global_yearly_summary`** — one row per `observation_year`.
   Columns: `observation_year, station_count, country_count, observation_count,
   avg_tmax_celsius, avg_tmin_celsius, avg_precip_mm`.
   Two-stage temp averaging (per-station then global). Feeds KPI Big Numbers and
   the temperature trend line.
2. **`noaa_ghcn_station_coverage_per_country`** — one row per country.
   Columns: `country_id, country_name, station_count, avg_elevation_m,
   avg_latitude, avg_longitude`. Built from `noaa_ghcn_stations` +
   `noaa_ghcn_countries`. Feeds the coverage bar.
3. **`noaa_ghcn_snow_and_cold_per_country`** — per country-year.
   Columns: `country_id, country_name, observation_year,
   avg_yearly_snowfall_mm (SNOW), min_tmin_celsius`. Feeds the snow/cold panel.

All new models follow existing conventions: `{{ ref(...) }}` to cleansed models,
`WHERE quality_flag IS NULL`, ÷10 unit scaling, INNER JOIN to countries for names.

## Superset assets (`helm/reporting/assets/`)

Managed as code, imported idempotently at pod startup (existing wrapper chart).

### Datasets (`datasets/warehouse/`)
- 3 new, one per new curated model (schema `curated`, `database_uuid` = Warehouse).
- Reuse existing `noaa_ghcn_avg_yearly_observations_per_country`.
- Each dataset lists physical columns + a `count` metric; no calculated columns,
  no custom SQL (`sql: null`) — pure physical tables.

### Charts (`charts/`)
- 4× `big_number_total` — total stations, total countries, total observations,
  global avg tmax — from `global_yearly_summary`.
- `countries_average_max_temperature` — `world_map` (exists).
- `global_temperature_trend` — `line` / time-series bar over `observation_year`
  (tmax + tmin) from `global_yearly_summary`.
- `top_countries_precipitation` — `bar` (row limit ~15, sorted desc) from
  per-country model.
- `station_coverage_by_country` — `bar` from station coverage model.
- `snow_and_cold_extremes` — `bar` (avg snowfall, sorted desc) from snow model.

### Dashboard (`dashboards/global_historical_climatology_network.yaml`)
Layout rows (top → bottom):
1. 4 KPI Big Numbers.
2. World map (wide).
3. Temperature trend line | Top precipitation bar.
4. Station coverage bar | Snow & cold bar.

Keep existing `uuid: 031c5ece-8758-406b-9ba6-be6325c7fccb`, `published: true`.
`metadata.chart_configuration` / `global_chart_configuration` updated for the new
chart set (native filters kept minimal).

## Build & verify

1. Write new dbt models; `dbt run` (or via Dagster) to build `curated` tables.
2. Confirm tables/columns via `kubectl exec svc/warehouse-clickhouse-headless --
   clickhouse-client --query "..."`.
3. Author dataset + chart + dashboard YAML mirroring existing working examples
   (world_map chart, per-country dataset, current dashboard) for exact viz params.
4. `helm dependency build helm/reporting` (if needed) then
   `helm upgrade --install reporting helm/reporting -n os-data-platform`.
5. bootstrapScript runs `superset import-directory --overwrite --force`.
6. Verify via Superset API: 1 database (unchanged), datasets/charts/dashboard
   counts increased; open dashboard renders all panels.

## Risks

- Hand-authored Superset chart YAML viz params are fiddly. Mitigation: mirror the
  existing exported examples exactly; validate by import + API/render check; if a
  chart fails, build it once in the UI and re-export via
  `helm/reporting/scripts/export_assets.sh`.
- Only 3 years of data → trend line is short; acceptable, this is the real dataset.
- ClickHouse `warehouse` connection is no-auth (documented); no credential change.

## Out of scope (YAGNI)

- No new database connections.
- No alerting/reports, no RLS, no per-user filters beyond a basic year filter.
- No changes to ingestion or cleansed layers.
