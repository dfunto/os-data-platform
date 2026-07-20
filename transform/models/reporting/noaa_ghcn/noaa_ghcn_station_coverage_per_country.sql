-- One row per country: station coverage and mean geography.
-- Elevation sentinel (-999.9 = missing) excluded from the average.
SELECT
  country_id,
  country_name,
  count(id) AS station_count,
  avgIf(elevation, elevation > -900) AS avg_elevation_m,
  avg(latitude) AS avg_latitude,
  avg(longitude) AS avg_longitude
FROM {{ ref('curated_noaa_ghcn_stations') }}
GROUP BY
  country_id,
  country_name
ORDER BY station_count DESC
