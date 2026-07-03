{{ config(materialized='view', alias='noaa_ghcn_quality_flags') }}
SELECT *
FROM {{ ref('noaa_ghcn_quality_flags') }}
