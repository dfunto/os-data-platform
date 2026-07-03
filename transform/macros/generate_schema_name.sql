{#
  Use the schema configured on the node verbatim (raw, cleansed) instead of
  dbt's default "<target_schema>_<custom_schema>" concatenation. This keeps the
  ClickHouse database names stable and makes Dagster asset keys line up with the
  ingestion assets (raw_noaa_ghcn_*).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
