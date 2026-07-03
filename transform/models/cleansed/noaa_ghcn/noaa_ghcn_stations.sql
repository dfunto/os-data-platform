SELECT
    TRIM(station_id) as id,
    CAST(TRIM(latitude) as Decimal(9, 6)) as latitude,
    CAST(TRIM(longitude) as Decimal(9, 6)) as longitude,
    CAST(TRIM(elevation) as Decimal(8, 1)) as elevation,
    TRIM(state) as state_id,
    SUBSTRING(station_id, 1, 2) as country_id,
    TRIM(name) as name,
    TRIM(gsn_flag) as gsn_flag,
    TRIM(hcn_crn_flag) as hcn_crn_flag,
    TRIM(wmo_id) as wmo_id
FROM {{ source('raw', 'noaa_ghcn_stations') }}
