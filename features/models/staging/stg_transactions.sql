with source as (
    select * from {{ source('raw', 'transactions') }}
),

renamed as (
    select
        invoice_id,
        product_id,
        description                                 as product_name,
        cast(quantity as integer)                   as quantity,
        cast(invoice_date as timestamp)             as invoice_ts,
        cast(invoice_date as date)                  as invoice_date,
        cast(unit_price as double)                  as unit_price,
        cast(customer_id as integer)                as customer_id,
        country,
        cast(revenue as double)                     as revenue,
        -- derived
        extract('year' from cast(invoice_date as timestamp))    as tx_year,
        extract('month' from cast(invoice_date as timestamp))   as tx_month,
        extract('hour' from cast(invoice_date as timestamp))    as tx_hour,
        extract('dow' from cast(invoice_date as timestamp))     as tx_dow
    from source
)

select * from renamed
