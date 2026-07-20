{{ config(alias='noaa_ghcn_stations') }}
-- Denormalized station dimension: station attributes with country and state
-- names joined in. Elevation keeps its raw sentinel (-999.9 = missing); the
-- exclusion is a consumer-side filter, not baked here.
SELECT
  stations.id AS id,
  stations.country_id,
  countries.name AS country_name,
  stations.state_id,
  states.name AS state_name,
  stations.latitude,
  stations.longitude,
  stations.elevation,
  stations.name AS name,
  stations.gsn_flag,
  stations.hcn_crn_flag,
  stations.wmo_id
FROM {{ ref('noaa_ghcn_stations') }} stations
LEFT JOIN {{ ref('noaa_ghcn_countries') }} countries
  ON stations.country_id = countries.id
LEFT JOIN {{ ref('noaa_ghcn_states') }} states
  ON stations.state_id = states.id
