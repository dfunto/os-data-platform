MODEL (
  name cleansed.noaa_ghcn_countries,
  kind FULL,
  grain id,
  tags [noaa_ghcn]
);
SELECT
  TRIM(code) as id,
  TRIM(name) as name
FROM raw.noaa_ghcn_countries
