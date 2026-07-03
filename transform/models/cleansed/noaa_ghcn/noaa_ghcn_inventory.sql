SELECT
    TRIM(station_id) as station_id,
    CAST(TRIM(latitude) as Decimal(9, 6)) as latitude,
    CAST(TRIM(longitude) as Decimal(9, 6)) as longitude,
    TRIM(element) as element,
    CAST(first_year as Integer) as first_year,
    CAST(last_year as Integer) as last_year
FROM {{ source('raw', 'noaa_ghcn_inventory') }}
