select
    user_id,
    product_id,
    product_name,
    department,
    aisle,
    total_orders,
    reorder_count,
    interaction_score
from {{ ref('int_user_product_interactions') }}
where interaction_score > 0
