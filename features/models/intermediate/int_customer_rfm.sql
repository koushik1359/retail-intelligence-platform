with tx as (
    select * from {{ ref('stg_transactions') }}
),

rfm_raw as (
    select
        customer_id,
        max(country)                            as country,
        max(invoice_date)                       as last_purchase_date,
        count(distinct invoice_id)              as frequency,
        sum(revenue)                            as monetary_value,
        count(distinct invoice_date)            as active_days
    from tx
    group by 1
),

rfm_scored as (
    select
        *,
        -- recency in days from last transaction in dataset
        datediff('day', last_purchase_date,
            (select max(invoice_date) from tx))     as recency_days,
        -- simple RFM tiers
        case
            when frequency >= 20 then 5
            when frequency >= 10 then 4
            when frequency >= 5  then 3
            when frequency >= 2  then 2
            else 1
        end                                         as frequency_score,
        case
            when monetary_value >= 5000 then 5
            when monetary_value >= 2000 then 4
            when monetary_value >= 1000 then 3
            when monetary_value >= 500  then 2
            else 1
        end                                         as monetary_score
    from rfm_raw
)

select * from rfm_scored
