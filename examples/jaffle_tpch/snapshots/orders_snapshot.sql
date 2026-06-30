{% snapshot orders_snapshot %}
{{ config(
    target_schema='dbt_jaffle',
    unique_key='o_orderkey',
    strategy='timestamp',
    updated_at='order_ts'
) }}
select
    o_orderkey,
    o_custkey,
    o_orderstatus,
    o_totalprice,
    cast(o_orderdate as timestamp) as order_ts
from {{ source('tpch', 'orders') }}
where o_orderkey <= 100
{% endsnapshot %}
