SELECT
    TRIM(code) as id,
    TRIM(name) as name
FROM {{ source('raw', 'noaa_ghcn_states') }}
