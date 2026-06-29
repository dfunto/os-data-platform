MODEL (
  name cleansed.noaa_ghcn_stations,
  kind FULL,
  grain station_id
);
SELECT
    station_id,
    CAST(latitude as Decimal(9, 6)) as latitude,
    CAST(longitude as Decimal(9, 6)) as longitude,
    CAST(elevation as Decimal(8, 1)) as elevation,
    TRIM(state) as state_id,
    TRIM(name) as name,
    gsn_flag,
    hcn_crn_flag,
    TRIM(wmo_id) wmo_id
FROM raw.noaa_ghcn_stations