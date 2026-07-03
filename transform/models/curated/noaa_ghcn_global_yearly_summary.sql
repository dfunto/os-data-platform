-- One row per observation_year: global climate summary.
-- Temperatures use two-stage averaging (per station, then across stations) to
-- match noaa_ghcn_avg_yearly_observations_per_country. Raw temp/precip are tenths
-- (÷10 -> °C / mm). Only quality_flag IS NULL rows (passed GHCN QC) are kept.
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
    observation_year,
    station_id,
    avgOrNullIf(observation_value, measure = 'TMAX') / 10 AS avg_tmax_celsius,
    avgOrNullIf(observation_value, measure = 'TMIN') / 10 AS avg_tmin_celsius,
    sumOrNullIf(observation_value, measure = 'PRCP') / 10 AS total_precip_mm
  FROM observations
  GROUP BY observation_year, station_id
),
temps AS (
  SELECT
    observation_year,
    count(station_id) AS station_count,
    avg(avg_tmax_celsius) AS avg_tmax_celsius,
    avg(avg_tmin_celsius) AS avg_tmin_celsius,
    avg(total_precip_mm) AS avg_precip_mm
  FROM per_station
  GROUP BY observation_year
),
counts AS (
  SELECT
    obs.observation_year AS observation_year,
    count() AS observation_count,
    countDistinct(stations.country_id) AS country_count
  FROM {{ ref('noaa_ghcn_observations') }} obs
  INNER JOIN {{ ref('noaa_ghcn_stations') }} stations
    ON obs.station_id = stations.id
  WHERE obs.quality_flag IS NULL
  GROUP BY obs.observation_year
)
SELECT
  temps.observation_year,
  temps.station_count,
  counts.country_count,
  counts.observation_count,
  temps.avg_tmax_celsius,
  temps.avg_tmin_celsius,
  temps.avg_precip_mm
FROM temps
INNER JOIN counts ON temps.observation_year = counts.observation_year
ORDER BY temps.observation_year