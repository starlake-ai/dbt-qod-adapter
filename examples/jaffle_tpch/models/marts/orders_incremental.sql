{{ config(
    materialized='incremental',
    unique_key='order_key',
    incremental_strategy='delete+insert'
) }}

select
    order_key,
    customer_key,
    order_status,
    total_price,
    order_date
from {{ ref('stg_orders') }}

{% if is_incremental() %}
-- only load orders newer than what we already have
where order_date > (select coalesce(max(order_date), '1900-01-01') from {{ this }})
{% endif %}
