with source as (
    select * from {{ source('raw', 'instacart_interactions') }}
),

renamed as (
    select
        cast(order_id as integer)                   as order_id,
        cast(user_id as integer)                    as user_id,
        cast(product_id as integer)                 as product_id,
        product_name,
        aisle,
        department,
        cast(add_to_cart_order as integer)          as cart_position,
        cast(reordered as boolean)                  as is_reorder,
        cast(order_number as integer)               as order_number,
        cast(order_dow as integer)                  as order_dow,
        cast(order_hour_of_day as integer)          as order_hour,
        cast(days_since_prior_order as double)      as days_since_prior_order
    from source
)

select * from renamed
