CREATE OR REPLACE TABLE raw.`{{ source_name }}_{{ table_name }}`
{% if columns %}({% for col in columns %}`{{ col.name }}` {{ col.type }}{% if not loop.last %}, {% endif %}{% endfor %}){% endif %}
ENGINE = S3(seaweedfs, filename='{{ prefix }}', format='{{ file_format }}')
{% if settings %}SETTINGS {% for k, v in settings.items() %}{{ k }} = '{{ v }}'{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
