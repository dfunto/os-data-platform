MODEL (
  name cleansed.noaa_ghcn_quality_flags,
  kind VIEW,
  grain id,
  tags [noaa_ghcn, seed]
);
SELECT *
FROM raw.noaa_ghcn_quality_flags