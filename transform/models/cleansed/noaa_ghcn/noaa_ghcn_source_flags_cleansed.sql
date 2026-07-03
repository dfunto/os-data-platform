{{ config(materialized='view', alias='noaa_ghcn_source_flags') }}
SELECT *
FROM {{ ref('noaa_ghcn_source_flags') }}
