{# Catalog macro for `dbt docs generate`. DuckDB exposes a single unqualified
   information_schema spanning catalogs (filter by table_catalog). Returns one row
   per column with the table_/column_ keys dbt's catalog builder expects. #}

{% macro qod__get_catalog(information_schema, schemas) -%}
  {% set query %}
    select
      t.table_catalog as "table_database",
      t.table_schema  as "table_schema",
      t.table_name    as "table_name",
      case when t.table_type = 'VIEW' then 'view' else 'table' end as "table_type",
      ''              as "table_comment",
      ''              as "table_owner",
      c.column_name      as "column_name",
      c.ordinal_position as "column_index",
      c.data_type        as "column_type",
      ''                 as "column_comment"
    from information_schema.tables t
    join information_schema.columns c
      on  c.table_catalog = t.table_catalog
      and c.table_schema  = t.table_schema
      and c.table_name    = t.table_name
    where t.table_catalog = '{{ information_schema.database }}'
      and (
        {%- if schemas -%}
          {%- for schema in schemas -%}
            t.table_schema = '{{ schema }}'{% if not loop.last %} or {% endif %}
          {%- endfor -%}
        {%- else -%}
          1 = 0
        {%- endif -%}
      )
    order by t.table_schema, t.table_name, c.ordinal_position
  {% endset %}
  {{ return(run_query(query)) }}
{%- endmacro %}