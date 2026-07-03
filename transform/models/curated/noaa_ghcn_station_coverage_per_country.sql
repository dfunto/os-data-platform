-- One row per country: station coverage and mean geography.
-- Elevation sentinel (-999.9 = missing) excluded from the average.
SELECT
  stations.country_id,
  countries.name AS country_name,
  count(stations.id) AS station_count,
  avgIf(stations.elevation, stations.elevation > -900) AS avg_elevation_m,
  avg(stations.latitude) AS avg_latitude,
  avg(stations.longitude) AS avg_longitude
FROM {{ ref('noaa_ghcn_stations') }} stations
INNER JOIN {{ ref('noaa_ghcn_countries') }} countries
  ON stations.country_id = countries.id
GROUP BY stations.country_id, country_name
ORDER BY station_count DESC
