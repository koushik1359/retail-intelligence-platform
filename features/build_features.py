import duckdb
import pyarrow.parquet as pq
import os
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
OUT = "data/processed"
os.makedirs(OUT, exist_ok=True)

print("Building item-level features via DuckDB window functions...")
print("Base data: 2014-01-01 → present  |  Output rows: 2015-06-01 → present")

con = duckdb.connect(DUCKDB_PATH, read_only=True)

query = """
WITH base AS (
    SELECT
        item_id,
        store_id,
        dept_id,
        cat_id,
        state_id,
        CAST(date AS DATE)          AS sale_date,
        CAST(unit_sales AS FLOAT)   AS unit_sales,
        CAST(sell_price AS FLOAT)   AS sell_price,
        event_name_1,
        event_type_1,
        snap_CA,
        snap_TX,
        snap_WI
    FROM raw.m5_sales
    WHERE date >= '2014-01-01'
),

with_features AS (
    SELECT
        item_id, store_id, dept_id, cat_id, state_id,
        sale_date, unit_sales, sell_price,

        -- Calendar
        CAST(EXTRACT('dow'   FROM sale_date) AS SMALLINT)   AS day_of_week,
        CAST(EXTRACT('day'   FROM sale_date) AS SMALLINT)   AS day_of_month,
        CAST(EXTRACT('week'  FROM sale_date) AS SMALLINT)   AS week_of_year,
        CAST(EXTRACT('month' FROM sale_date) AS SMALLINT)   AS month,
        CAST(EXTRACT('year'  FROM sale_date) AS SMALLINT)   AS year,
        CASE WHEN EXTRACT('dow' FROM sale_date) IN (0,6) THEN 1 ELSE 0 END  AS is_weekend,
        CASE WHEN EXTRACT('day' FROM sale_date) <= 3   THEN 1 ELSE 0 END    AS is_month_start,
        CASE WHEN EXTRACT('day' FROM sale_date) >= 28  THEN 1 ELSE 0 END    AS is_month_end,

        -- Event features
        CASE WHEN event_name_1 != 'None' THEN 1 ELSE 0 END  AS is_event,
        CASE event_type_1
            WHEN 'Sporting'  THEN 1
            WHEN 'Cultural'  THEN 2
            WHEN 'National'  THEN 3
            WHEN 'Religious' THEN 4
            ELSE 0
        END                                                  AS event_type,

        -- SNAP flag (state-specific)
        CASE state_id
            WHEN 'CA' THEN snap_CA
            WHEN 'TX' THEN snap_TX
            WHEN 'WI' THEN snap_WI
            ELSE 0
        END                                                  AS is_snap,

        -- Lag features (shift 1 day)
        LAG(unit_sales, 1)   OVER w   AS units_lag_1,
        LAG(unit_sales, 7)   OVER w   AS units_lag_7,
        LAG(unit_sales, 14)  OVER w   AS units_lag_14,
        LAG(unit_sales, 28)  OVER w   AS units_lag_28,
        LAG(unit_sales, 364) OVER w   AS units_lag_364,
        LAG(sell_price, 1)   OVER w   AS price_lag_1,
        LAG(sell_price, 7)   OVER w   AS price_lag_7,

        -- Rolling means (rows t-1 to t-N, no leakage)
        AVG(unit_sales) OVER (
            PARTITION BY store_id, item_id ORDER BY sale_date
            ROWS BETWEEN 7  PRECEDING AND 1 PRECEDING)     AS units_roll_mean_7,
        AVG(unit_sales) OVER (
            PARTITION BY store_id, item_id ORDER BY sale_date
            ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING)     AS units_roll_mean_14,
        AVG(unit_sales) OVER (
            PARTITION BY store_id, item_id ORDER BY sale_date
            ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)     AS units_roll_mean_28,

        -- Rolling std
        STDDEV(unit_sales) OVER (
            PARTITION BY store_id, item_id ORDER BY sale_date
            ROWS BETWEEN 7  PRECEDING AND 1 PRECEDING)     AS units_roll_std_7,
        STDDEV(unit_sales) OVER (
            PARTITION BY store_id, item_id ORDER BY sale_date
            ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)     AS units_roll_std_28,

        -- Price rolling mean
        AVG(sell_price) OVER (
            PARTITION BY store_id, item_id ORDER BY sale_date
            ROWS BETWEEN 7  PRECEDING AND 1 PRECEDING)     AS price_roll_mean_7,

        -- Expanding mean (long-term item baseline)
        AVG(unit_sales) OVER (
            PARTITION BY store_id, item_id ORDER BY sale_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS units_expanding_mean

    FROM base
    WINDOW w AS (PARTITION BY store_id, item_id ORDER BY sale_date)
)

SELECT * FROM with_features
WHERE sale_date >= '2015-06-01'
  AND units_lag_28  IS NOT NULL
  AND units_lag_364 IS NOT NULL
ORDER BY store_id, item_id, sale_date
"""

out_path = f"{OUT}/m5_item_features.parquet"
print("Running query (may take 5–10 min on first run)...")
con.execute(f"COPY ({query}) TO '{out_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
con.close()

meta = pq.read_metadata(out_path)
size_gb = os.path.getsize(out_path) / 1e9
print(f"\n✓ Saved to {out_path}")
print(f"  Rows:    {meta.num_rows:,}")
print(f"  Columns: {meta.num_columns}")
print(f"  Size:    {size_gb:.2f} GB")
