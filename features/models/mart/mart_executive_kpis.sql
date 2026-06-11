with tx as (
    select * from {{ ref('stg_transactions') }}
),

daily_summary as (
    select
        invoice_date                                                    as kpi_date,
        count(distinct invoice_id)                                      as total_orders,
        count(distinct customer_id)                                     as unique_customers,
        sum(quantity)                                                   as total_units,
        sum(revenue)                                                    as total_revenue,
        sum(revenue) / nullif(count(distinct invoice_id), 0)           as avg_basket_size,
        count(distinct product_id)                                      as unique_products_sold
    from tx
    group by 1
),

with_trends as (
    select
        *,
        sum(total_revenue) over (
            order by kpi_date
            rows between 6 preceding and current row
        )                                                               as revenue_7d_rolling,
        avg(total_revenue) over (
            order by kpi_date
            rows between 28 preceding and 1 preceding
        )                                                               as revenue_28d_baseline,
        lag(total_revenue, 7) over (order by kpi_date)                 as revenue_last_week,
        lag(total_orders,  7) over (order by kpi_date)                 as orders_last_week,
        lag(unique_customers, 7) over (order by kpi_date)              as customers_last_week
    from daily_summary
)

select
    kpi_date,
    total_orders,
    unique_customers,
    total_units,
    round(total_revenue, 2)                                             as total_revenue,
    round(avg_basket_size, 2)                                          as avg_basket_size,
    unique_products_sold,
    round(revenue_7d_rolling, 2)                                       as revenue_7d_rolling,
    round(revenue_28d_baseline, 2)                                     as revenue_28d_baseline,
    round(revenue_last_week, 2)                                        as revenue_last_week,
    orders_last_week,
    customers_last_week,
    case
        when revenue_last_week > 0
        then round(100.0 * (total_revenue - revenue_last_week) / revenue_last_week, 2)
    end                                                                 as revenue_wow_pct,
    case
        when revenue_28d_baseline > 0
         and total_revenue > 2.0 * revenue_28d_baseline
        then true else false
    end                                                                 as is_revenue_spike
from with_trends
order by kpi_date
