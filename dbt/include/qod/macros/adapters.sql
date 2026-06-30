{# =========================================================================
   DuckDB-dialect adapter macros for the Quack-on-Demand FlightSQL edge.
   The backend is DuckDB Quack + DuckLake, so most of dbt's default macros
   apply; these override the catalog/metadata macros that have no default and
   the handful of statements where DuckDB/DuckLake differ.
   ========================================================================= #}

{# ---- Catalog / metadata (no usable default) ---- #}

{# DuckDB exposes a single unqualified `information_schema` spanning all attached
   catalogs, with catalog_name / table_catalog columns. There is no
   `<catalog>.information_schema`, so filter by the catalog column instead. #}

{% macro qod__list_schemas(database) -%}
  {% call statement('list_schemas', fetch_result=True, auto_begin=False) %}
    select distinct schema_name
    from information_schema.schemata
    where catalog_name = '{{ database }}'
  {% endcall %}
  {{ return(load_result('list_schemas').table) }}
{%- endmacro %}


{% macro qod__check_schema_exists(information_schema, schema) -%}
  {% call statement('check_schema_exists', fetch_result=True, auto_begin=False) %}
    select count(*)
    from information_schema.schemata
    where catalog_name = '{{ information_schema.database }}'
      and schema_name = '{{ schema }}'
  {% endcall %}
  {{ return(load_result('check_schema_exists').table) }}
{%- endmacro %}


{% macro qod__list_relations_without_caching(schema_relation) %}
  {% call statement('list_relations_without_caching', fetch_result=True, auto_begin=False) %}
    select
      table_catalog as database,
      table_name    as name,
      table_schema  as schema,
      case when table_type = 'VIEW' then 'view' else 'table' end as type
    from information_schema.tables
    where table_catalog = '{{ schema_relation.database }}'
      and table_schema = '{{ schema_relation.schema }}'
  {% endcall %}
  {{ return(load_result('list_relations_without_caching').table) }}
{% endmacro %}


{% macro qod__get_columns_in_relation(relation) -%}
  {% call statement('get_columns_in_relation', fetch_result=True, auto_begin=False) %}
    select
      column_name,
      data_type,
      character_maximum_length,
      numeric_precision,
      numeric_scale
    from information_schema.columns
    where table_catalog = '{{ relation.database }}'
      and table_schema = '{{ relation.schema }}'
      and table_name = '{{ relation.identifier }}'
    order by ordinal_position
  {% endcall %}
  {% set table = load_result('get_columns_in_relation').table %}
  {{ return(sql_convert_columns_in_relation(table)) }}
{%- endmacro %}


{# ---- Relation lifecycle ---- #}

{# Pool-safety: never create DuckDB TEMP tables (they are node-local and a
   pool's statements may route to a different node). dbt asks for a "temporary"
   intermediate during table/incremental/snapshot flows; we materialize it as a
   real, fully-qualified DuckLake table (visible across the pool) and dbt drops
   it afterward. So `temporary` is intentionally ignored here. #}
{% macro qod__create_table_as(temporary, relation, sql) -%}
  {%- set sql_header = config.get('sql_header', none) -%}
  {{ sql_header if sql_header is not none }}
  create or replace table {{ relation }} as (
    {{ sql }}
  )
{%- endmacro %}


{% macro qod__create_view_as(relation, sql) -%}
  {%- set sql_header = config.get('sql_header', none) -%}
  {{ sql_header if sql_header is not none }}
  create or replace view {{ relation }} as (
    {{ sql }}
  )
{%- endmacro %}


{% macro qod__drop_relation(relation) -%}
  {% call statement('drop_relation', auto_begin=False) -%}
    drop {{ relation.type }} if exists {{ relation }}
  {%- endcall %}
{%- endmacro %}


{% macro qod__rename_relation(from_relation, to_relation) -%}
  {#- DuckDB is strict: ALTER TABLE only renames tables, ALTER VIEW only views.
      We can't trust from_relation.type here: dbt's incremental materialization
      renames `target_relation` (typed as the NEW materialization, e.g. table)
      even when the on-disk object is still a view. So resolve the ACTUAL current
      type from information_schema and pick the right keyword. -#}
  {% set type_query %}
    select case when table_type = 'VIEW' then 'view' else 'table' end as kind
    from information_schema.tables
    where table_catalog = '{{ from_relation.database }}'
      and table_schema = '{{ from_relation.schema }}'
      and table_name = '{{ from_relation.identifier }}'
  {% endset %}
  {% set result = run_query(type_query) %}
  {% set kind = result[0][0] if (result is not none and result | length > 0) else from_relation.type %}
  {% call statement('rename_relation', auto_begin=False) -%}
    alter {{ kind }} {{ from_relation }} rename to {{ to_relation.identifier }}
  {%- endcall %}
{%- endmacro %}


{# DuckLake may not support TRUNCATE; DELETE is equivalent for dbt's purposes. #}
{% macro qod__truncate_relation(relation) -%}
  {% call statement('truncate_relation', auto_begin=False) -%}
    delete from {{ relation }}
  {%- endcall %}
{%- endmacro %}


{% macro qod__create_schema(relation) -%}
  {% call statement('create_schema', auto_begin=False) -%}
    create schema if not exists {{ relation.without_identifier() }}
  {%- endcall %}
{%- endmacro %}


{% macro qod__drop_schema(relation) -%}
  {% call statement('drop_schema', auto_begin=False) -%}
    drop schema if exists {{ relation.without_identifier() }} cascade
  {%- endcall %}
{%- endmacro %}


{% macro qod__current_timestamp() -%}
  now()
{%- endmacro %}


{% macro qod__snapshot_string_as_time(timestamp) -%}
  {{ return("'" ~ timestamp ~ "'::timestamp") }}
{%- endmacro %}


{# ---- Seeds ----
   The edge does not implement parameter-bound statements (it returns
   `Unimplemented; ExecuteQuery` for bindings), so dbt's default seed loader
   (which binds values via `%s`) fails. Override it to inline literal values. #}

{% macro qod__seed_literal(value) -%}
  {%- if value is none -%}null
  {%- elif value is boolean -%}{{ 'true' if value else 'false' }}
  {%- elif value is number -%}{{ value }}
  {%- else -%}'{{ value | string | replace("'", "''") }}'
  {%- endif -%}
{%- endmacro %}


{% macro qod__load_csv_rows(model, agate_table) %}
  {% set batch_size = get_batch_size() %}
  {% set cols_sql = get_seed_column_quoted_csv(model, agate_table.column_names) %}
  {% set statements = [] %}

  {% for chunk in agate_table.rows | batch(batch_size) %}
    {% set sql %}
      insert into {{ this.render() }} ({{ cols_sql }}) values
      {% for row in chunk -%}
        ({%- for col in row -%}
          {{ qod__seed_literal(col) }}{%- if not loop.last %}, {% endif -%}
        {%- endfor -%}){%- if not loop.last %},{% endif %}
      {%- endfor %}
    {% endset %}
    {% do adapter.add_query(sql, abridge_sql_log=True) %}
    {% if loop.index0 == 0 %}
      {% do statements.append(sql) %}
    {% endif %}
  {% endfor %}

  {{ return(statements[0] if statements else '') }}
{% endmacro %}