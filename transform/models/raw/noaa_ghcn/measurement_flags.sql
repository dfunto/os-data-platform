MODEL (
  name raw.noaa_ghcn_measurement_flags,
  kind SEED (
    path '../../../seeds/noaa_ghcn/measurement_flags.csv'
  ),
  grain id,
  tags [noaa_ghcn, seed]
);