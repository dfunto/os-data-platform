MODEL (
  name cleansed.noaa_ghcn_observations,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column observation_date
  ),
  grain (observation_date, station_id, measure),
  physical_properties (
    partition_by = 'observation_year',
    order_by = '(observation_date, station_id, measure)'
  ),
  tags [noaa_ghcn]
);
SELECT
  `YEAR` as observation_year,
  ID as station_id,
  toDate(toString(DATE), '%Y%m%d') as observation_date,
  CASE
    WHEN OBS_TIME IS NOT NULL AND OBS_TIME != ''
      THEN parseDateTimeBestEffort(concat(toString(DATE), ' ', lpad(toString(OBS_TIME), 4, '0')))
    ELSE NULL
  END as observed_at,
  DATA_VALUE as observation_value,
  M_FLAG as measurement_flag,
  Q_FLAG as quality_flag,
  S_FLAG as source_flag,
  ELEMENT as measure
FROM "raw"."noaa_ghcn_observations"
