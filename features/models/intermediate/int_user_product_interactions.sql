with base as (
    select
        user_id,
        product_id,
        product_name,
        department,
        aisle,
        count(distinct order_id)                as total_orders,
        sum(case when is_reorder then 1 else 0 end) as reorder_count,
        min(order_number)                       as first_order_number,
        max(order_number)                       as last_order_number,
        avg(cart_position)                      as avg_cart_position
    from {{ ref('stg_instacart_interactions') }}
    group by 1, 2, 3, 4, 5
),

scored as (
    select
        *,
        -- implicit feedback score: log of orders + reorder bonus
        ln(1 + total_orders) + (0.5 * ln(1 + reorder_count)) as interaction_score
    from base
)

select * from scored
