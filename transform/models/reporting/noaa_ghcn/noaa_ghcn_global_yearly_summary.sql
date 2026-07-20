-- One row per year: global climate summary. Two-stage temps come from the
-- station-year fact; counts sum/distinct over the same fact.
SELECT
  sy.observation_year,
  countIf(
    sy.avg_tmax_celsius IS NOT NULL
    OR sy.avg_tmin_celsius IS NOT NULL
    OR sy.total_precip_mm IS NOT NULL
  ) AS station_count,
  countDistinct(sy.country_id) AS country_count,
  sum(sy.observation_count) AS observation_count,
  avg(sy.avg_tmax_celsius) AS avg_tmax_celsius,
  avg(sy.avg_tmin_celsius) AS avg_tmin_celsius,
  avg(sy.total_precip_mm) AS avg_precip_mm
FROM {{ ref('curated_noaa_ghcn_station_year') }} AS sy
GROUP BY sy.observation_year
ORDER BY sy.observation_year
