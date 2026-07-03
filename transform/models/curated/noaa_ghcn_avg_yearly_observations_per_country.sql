-- Yearly per-country climate summary.
-- Two-stage aggregation: average per station first, then across stations,
-- so station-dense countries don't dominate the country average.
-- Only quality_flag IS NULL rows are kept (passed all GHCN QC checks).
-- Temperatures reported in °C, precipitation in mm (raw values are tenths).
WITH observations AS (
  SELECT
    observation_year,
    station_id,
    measure,
    observation_value
  FROM {{ ref('noaa_ghcn_observations') }}
  WHERE quality_flag IS NULL
    AND measure IN ('TMAX', 'TMIN', 'PRCP')
),
per_station AS (
  SELECT
    observations.observation_year,
    stations.country_id,
    observations.station_id,
    avgOrNullIf(observations.observation_value, observations.measure = 'TMAX') / 10 AS avg_tmax_celsius,
    avgOrNullIf(observations.observation_value, observations.measure = 'TMIN') / 10 AS avg_tmin_celsius,
    sumOrNullIf(observations.observation_value, observations.measure = 'PRCP') / 10 AS total_precip_mm
  FROM observations
  INNER JOIN {{ ref('noaa_ghcn_stations') }} stations
    ON observations.station_id = stations.id
  GROUP BY
    observation_year,
    country_id,
    station_id
)
SELECT
  per_station.observation_year,
  per_station.country_id,
  countries.name AS country_name,
  count(per_station.station_id) AS station_count,
  avg(per_station.avg_tmax_celsius) AS avg_tmax_celsius,
  avg(per_station.avg_tmin_celsius) AS avg_tmin_celsius,
  avg(per_station.total_precip_mm) AS avg_yearly_precip_mm
FROM per_station
INNER JOIN {{ ref('noaa_ghcn_countries') }} countries
  ON per_station.country_id = countries.id
GROUP BY
  observation_year,
  country_id,
  country_name