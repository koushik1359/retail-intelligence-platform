with source as (
    select * from {{ source('raw', 'products') }}
),

renamed as (
    select
        product_id,
        product_name,
        category                                    as main_category,
        sub_category,
        cast(avg_rating as double)                  as rating,
        cast(rating_count as integer)               as rating_count,
        cast(sale_price as double)                  as discount_price,
        cast(list_price as double)                  as actual_price,
        cast(discount_pct as double)                as discount_pct,
        -- derived
        case
            when avg_rating >= 4.5 then 'excellent'
            when avg_rating >= 4.0 then 'good'
            when avg_rating >= 3.0 then 'average'
            else 'poor'
        end                                         as rating_tier,
        case
            when discount_pct >= 50 then 'high_discount'
            when discount_pct >= 20 then 'medium_discount'
            when discount_pct > 0  then 'low_discount'
            else 'no_discount'
        end                                         as discount_tier
    from source
    where product_name is not null
)

select * from renamed
