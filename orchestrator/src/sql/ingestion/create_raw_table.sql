CREATE TABLE IF NOT EXISTS raw.{{ source_name }}_{{ table_name }}
ENGINE = S3(seaweedfs, filename='{{ prefix }}/*.parquet')
