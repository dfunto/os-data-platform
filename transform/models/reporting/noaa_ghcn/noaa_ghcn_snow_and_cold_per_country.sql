-- Per country-year snow and cold extremes. Snow summed per station in the fact,
-- then averaged across stations here; min_tmin is the coldest station reading.
SELECT
  sy.observation_year,
  sy.country_id,
  sy.country_name,
  avg(sy.total_snowfall_mm) AS avg_yearly_snowfall_mm,
  min(sy.min_tmin_celsius) AS min_tmin_celsius
FROM {{ ref('curated_noaa_ghcn_station_year') }} AS sy
GROUP BY
  sy.observation_year,
  sy.country_id,
  sy.country_name
-- Match the previous per-station semantics: keep only country-years that had
-- snowfall or minimum-temperature readings (avoid all-NULL rows).
HAVING avg_yearly_snowfall_mm IS NOT NULL
    OR min_tmin_celsius IS NOT NULL
