{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by='observation_year',
    order_by=['observation_date', 'station_id', 'measure']
  )
}}
SELECT
  `YEAR` as observation_year,
  CAST(ID as String) as station_id,
  CAST(toDate(toString(DATE), '%Y%m%d') as Date) as observation_date,
  CASE
    WHEN OBS_TIME IS NOT NULL AND OBS_TIME != ''
      THEN toDateTime(toDate(toString(DATE), '%Y%m%d'))
        + toIntervalHour(toUInt16(substring(lpad(toString(OBS_TIME), 4, '0'), 1, 2)))
        + toIntervalMinute(toUInt16(substring(lpad(toString(OBS_TIME), 4, '0'), 3, 2)))
    ELSE NULL
  END as observed_at,
  DATA_VALUE as observation_value,
  M_FLAG as measurement_flag,
  Q_FLAG as quality_flag,
  S_FLAG as source_flag,
  CAST(ELEMENT AS String) as measure
FROM {{ source('raw', 'noaa_ghcn_observations') }}
{% if is_incremental() %}
WHERE `YEAR` BETWEEN toYear(toDate('{{ var("start_ds") }}')) AND toYear(toDate('{{ var("end_ds") }}'))
{% endif %}
