{% if schema_only %}
CREATE TABLE IF NOT EXISTS `{{ target_database }}`.`{{ target_table_name }}`
AS `{{ source_database }}`.`{{ source_table_name }}`;
{% else %}
CREATE TABLE IF NOT EXISTS `{{ target_database }}`.`{{ target_table_name }}`
ENGINE = MergeTree()
AS SELECT * FROM {{ source_database }}.`{{ source_table_name }}`;
{% endif %}