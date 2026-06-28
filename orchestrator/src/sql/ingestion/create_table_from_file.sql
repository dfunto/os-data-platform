CREATE OR REPLACE TABLE {{ database }}.`{{ source_name }}_{{ table_name }}`
ENGINE = MergeTree()
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