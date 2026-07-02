MODEL (
  name raw.noaa_ghcn_source_flags,
  kind SEED (
    path '../../../seeds/noaa_ghcn/source_flags.csv'
  ),
  grain id,
  tags [noaa_ghcn, seed]
);