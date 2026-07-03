{{ config(materialized='view', alias='noaa_ghcn_measurement_flags') }}
SELECT *
FROM {{ ref('noaa_ghcn_measurement_flags') }}
