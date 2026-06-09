with stores as (
    select distinct
        store_id,
        state_id,
        -- derive region from store_id prefix
        split_part(store_id, '_', 1)            as state_code,
        cast(split_part(store_id, '_', 2) as integer) as store_number
    from {{ ref('stg_m5_sales') }}
),

with_metrics as (
    select
        s.store_id,
        s.state_id,
        s.state_code,
        s.store_number,
        sum(d.total_revenue)                    as total_revenue_all_time,
        sum(d.total_units)                      as total_units_all_time,
        count(distinct d.sale_date)             as active_days,
        min(d.sale_date)                        as first_sale_date,
        max(d.sale_date)                        as last_sale_date
    from stores s
    left join {{ ref('int_daily_store_sales') }} d using (store_id)
    group by 1, 2, 3, 4
)

select * from with_metrics
