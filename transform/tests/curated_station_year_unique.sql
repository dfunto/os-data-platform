-- Fails if (observation_year, station_id) is not unique in the station-year fact.
SELECT observation_year, station_id, count() AS n
FROM {{ ref('curated_noaa_ghcn_station_year') }}
GROUP BY observation_year, station_id
HAVING n > 1
