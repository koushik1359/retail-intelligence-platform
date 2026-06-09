with tx as (
    select * from {{ ref('stg_transactions') }}
),

aggregated as (
    select
        product_id,
        max(product_name)                       as product_name,
        count(distinct customer_id)             as unique_customers,
        count(distinct invoice_id)              as total_invoices,
        sum(quantity)                           as total_units_sold,
        sum(revenue)                            as total_revenue,
        avg(unit_price)                         as avg_unit_price,
        count(distinct invoice_date)            as active_selling_days,
        min(invoice_date)                       as first_sale_date,
        max(invoice_date)                       as last_sale_date
    from tx
    group by 1
),

ranked as (
    select
        *,
        rank() over (order by total_revenue desc)       as revenue_rank,
        rank() over (order by total_units_sold desc)    as volume_rank,
        total_revenue / nullif(active_selling_days, 0)  as revenue_per_day
    from aggregated
)

select * from ranked
