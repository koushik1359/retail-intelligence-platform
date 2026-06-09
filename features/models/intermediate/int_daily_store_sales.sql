with daily as (
    select
        sale_date,
        store_id,
        state_id,
        dept_id,
        cat_id,
        count(distinct item_id)         as unique_items_sold,
        sum(unit_sales)                 as total_units,
        sum(revenue)                    as total_revenue,
        avg(sell_price)                 as avg_price,
        sum(has_sales)                  as items_with_sales,
        count(*)                        as total_rows
    from {{ ref('stg_m5_sales') }}
    group by 1, 2, 3, 4, 5
)

select * from daily
