{{ config(alias='noaa_ghcn_station_year') }}
-- Station-year rollup fact: the per-station "first stage" of the two-stage
-- averages, computed once over QC-passing rows. Reporting marts and the future
-- Cube layer both aggregate ACROSS stations over this fact with a trivial avg(),
-- so the multi-stage logic is never defined twice. Values come pre-normalized
-- from curated.noaa_ghcn_observations (no divide-by-10 here).
SELECT
  observation_year,
  station_id,
  country_id,
  country_name,
  avgOrNullIf(observation_value_normalized, measure = 'TMAX') AS avg_tmax_celsius,
  avgOrNullIf(observation_value_normalized, measure = 'TMIN') AS avg_tmin_celsius,
  minOrNullIf(observation_value_normalized, measure = 'TMIN') AS min_tmin_celsius,
  sumOrNullIf(observation_value_normalized, measure = 'PRCP') AS total_precip_mm,
  sumOrNullIf(observation_value_normalized, measure = 'SNOW') AS total_snowfall_mm,
  count() AS observation_count
FROM {{ ref('curated_noaa_ghcn_observations') }}
WHERE quality_flag IS NULL
GROUP BY
  observation_year,
  station_id,
  country_id,
  country_name
