{% if replace %}
CREATE OR REPLACE TABLE
{% else %}
CREATE TABLE IF NOT EXISTS
{% endif %}
{{ database }}.`{{ table_name }}`
ENGINE = MergeTree()
{% if partition_columns %}
PARTITION BY ({% for col in partition_columns %}{{ col }}{% if not loop.last %}, {% endif %}{% endfor %})
{% endif %}
AS
SELECT
{% if not columns %}*{% else %}
{% for col in columns %}
    {% if col.expression %}
        {{ col.expression }} AS `{{ col.name }}`
    {% elif has_headers %}
        CAST(`{{ col.name }}` AS {{ col.type }}) AS `{{ col.name }}`
    {% else %}
        CAST(`c{{ loop.index }}` AS {{ col.type }}) AS `{{ col.name }}`
    {% endif %}
    {% if not loop.last %}, {% endif %}
{% endfor %}
    , toDateTime('{{ ingested_at }}') AS `ingested_at`
{% endif %}
FROM s3(seaweedfs, filename='{{ prefix }}', format='{{ file_format }}')
{% if schema_only %}LIMIT 0{% endif %}
{% if settings %}
SETTINGS {% for k, v in settings.items() %}{{ k }} = '{{ v }}'{% if not loop.last %}, {% endif %}{% endfor %}
{% endif %}