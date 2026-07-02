MODEL (
  name raw.noaa_ghcn_quality_flags,
  kind SEED (
    path '../../../seeds/noaa_ghcn/quality_flags.csv'
  ),
  grain id,
  tags [noaa_ghcn, seed]
);