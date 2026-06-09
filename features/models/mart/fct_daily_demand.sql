with sales as (
    select * from {{ ref('int_daily_store_sales') }}
),

-- store-level baselines (28-day rolling avg for anomaly detection)
with_baseline as (
    select
        *,
        avg(total_revenue) over (
            partition by store_id
            order by sale_date
            rows between 28 preceding and 1 preceding
        ) as revenue_28d_avg,
        avg(total_units) over (
            partition by store_id
            order by sale_date
            rows between 28 preceding and 1 preceding
        ) as units_28d_avg
    from sales
)

select
    sale_date,
    store_id,
    state_id,
    dept_id,
    cat_id,
    total_units,
    total_revenue,
    avg_price,
    unique_items_sold,
    revenue_28d_avg,
    units_28d_avg,
    -- anomaly flag: >2x baseline is anomalous
    case when revenue_28d_avg > 0
         and total_revenue > (2.0 * revenue_28d_avg)
    then true else false end                        as is_revenue_spike
from with_baseline
