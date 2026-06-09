with source as (
    select * from {{ source('raw', 'm5_sales') }}
),

renamed as (
    select
        id                                          as sale_id,
        item_id,
        dept_id,
        cat_id,
        store_id,
        state_id,
        cast(date as date)                          as sale_date,
        cast(unit_sales as integer)                 as unit_sales,
        cast(sell_price as double)                  as sell_price,
        cast(revenue as double)                     as revenue,
        -- derived
        extract('year' from cast(date as date))     as sale_year,
        extract('month' from cast(date as date))    as sale_month,
        extract('dow' from cast(date as date))      as day_of_week,
        case when unit_sales > 0 then 1 else 0 end  as has_sales
    from source
    where date is not null
)

select * from renamed
