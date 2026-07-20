{{ config(alias='noaa_ghcn_observations') }}
-- Observation-grain one-big-table: every observation denormalized with station,
-- country and state attributes. All rows are kept (including failed QC) with the
-- quality_flag column so consumers filter. Units are normalized ONCE here:
--   tenths elements (TMAX/TMIN/TAVG/PRCP) -> divide by 10
--   SNOW/SNWD are native millimeters -> left as-is
-- observation_value keeps the raw value for traceability.
SELECT
  obs.observation_year,
  obs.observation_date,
  obs.observed_at,
  obs.station_id,
  obs.measure,
  obs.observation_value,
  CASE
    WHEN obs.measure IN ('TMAX', 'TMIN', 'TAVG', 'PRCP') THEN obs.observation_value / 10.0
    ELSE toFloat64(obs.observation_value)
  END AS observation_value_normalized,
  obs.measurement_flag,
  obs.quality_flag,
  obs.source_flag,
  stations.country_id,
  stations.country_name,
  stations.state_id,
  stations.latitude,
  stations.longitude,
  stations.elevation
FROM {{ ref('noaa_ghcn_observations') }} obs
LEFT JOIN {{ ref('curated_noaa_ghcn_stations') }} stations
  ON obs.station_id = stations.id
