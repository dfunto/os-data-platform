ALTER TABLE `{{ target_database }}`.`{{ target_table_name }}`
REPLACE PARTITION ({% for v in partition_values %}{{ v }}{% if not loop.last %}, {% endif %}{% endfor %})
FROM `{{ source_database }}`.`{{ source_table_name }}`;