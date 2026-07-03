-- Per country-year: snowfall and cold extremes.
-- GHCN SNOW is reported in mm (whole, not tenths) -> no ÷10.
-- TMIN is tenths of °C (÷10). Snowfall is summed per station then averaged across
-- stations; min_tmin is the coldest station reading in the country-year.
WITH observations AS (
  SELECT
    observation_year,
    station_id,
    measure,
    observation_value
  FROM {{ ref('noaa_ghcn_observations') }}
  WHERE quality_flag IS NULL
    AND measure IN ('SNOW', 'TMIN')
),
per_station AS (
  SELECT
    observation_year,
    station_id,
    sumOrNullIf(observation_value, measure = 'SNOW') AS total_snowfall_mm,
    minOrNullIf(observation_value, measure = 'TMIN') / 10 AS min_tmin_celsius
  FROM observations
  GROUP BY observation_year, station_id
)
SELECT
  per_station.observation_year,
  stations.country_id,
  countries.name AS country_name,
  avg(per_station.total_snowfall_mm) AS avg_yearly_snowfall_mm,
  min(per_station.min_tmin_celsius) AS min_tmin_celsius
FROM per_station
INNER JOIN {{ ref('noaa_ghcn_stations') }} stations
  ON per_station.station_id = stations.id
INNER JOIN {{ ref('noaa_ghcn_countries') }} countries
  ON stations.country_id = countries.id
GROUP BY per_station.observation_year, stations.country_id, country_name
