{{ config(materialized='table') }}

select
    c.market_segment,
    count(distinct c.customer_key) as customers,
    count(o.order_key)            as orders,
    sum(o.total_price)            as total_revenue
from {{ ref('stg_customer') }} c
left join {{ ref('stg_orders') }} o
    on o.customer_key = c.customer_key
group by c.market_segment
order by total_revenue desc
