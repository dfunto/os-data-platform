-- Per country-year climate averages (two-stage: per station in the station-year
-- fact, then across stations here). Reads curated only; no unit logic.
-- avg() ignores NULLs in ClickHouse, so stations missing a measure do not bias
-- the average; station_count counts stations that had any temp/precip reading,
-- matching the previous per-station semantics.
SELECT
  sy.observation_year,
  sy.country_id,
  sy.country_name,
  countIf(
    sy.avg_tmax_celsius IS NOT NULL
    OR sy.avg_tmin_celsius IS NOT NULL
    OR sy.total_precip_mm IS NOT NULL
  ) AS station_count,
  avg(sy.avg_tmax_celsius) AS avg_tmax_celsius,
  avg(sy.avg_tmin_celsius) AS avg_tmin_celsius,
  avg(sy.total_precip_mm) AS avg_yearly_precip_mm
FROM {{ ref('curated_noaa_ghcn_station_year') }} AS sy
GROUP BY
  sy.observation_year,
  sy.country_id,
  sy.country_name
-- Match the previous per-station semantics: exclude country-years with no
-- temperature/precipitation stations (they would otherwise be all-NULL rows).
HAVING station_count > 0
