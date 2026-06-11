import duckdb
import os

print("Loading cleaned data into DuckDB raw layer...")

conn = duckdb.connect("data/warehouse.duckdb")

# ── M5 Sales ──────────────────────────────────────────────────────────────────
print("\n[1/4] Loading M5 sales...")
conn.execute("""
    CREATE OR REPLACE TABLE raw.m5_sales AS
    SELECT * FROM read_parquet('data/processed/m5_clean.parquet')
""")
count = conn.execute("SELECT COUNT(*) FROM raw.m5_sales").fetchone()[0]
print(f"  ✓ raw.m5_sales: {count:,} rows")

# ── Instacart ─────────────────────────────────────────────────────────────────
print("\n[2/4] Loading Instacart interactions...")
conn.execute("""
    CREATE OR REPLACE TABLE raw.instacart_interactions AS
    SELECT * FROM read_parquet('data/processed/instacart_clean.parquet')
""")
count = conn.execute("SELECT COUNT(*) FROM raw.instacart_interactions").fetchone()[0]
print(f"  ✓ raw.instacart_interactions: {count:,} rows")

# ── Online Retail ─────────────────────────────────────────────────────────────
print("\n[3/4] Loading Online Retail transactions...")
conn.execute("""
    CREATE OR REPLACE TABLE raw.transactions AS
    SELECT * FROM read_parquet('data/processed/online_retail_clean.parquet')
""")
count = conn.execute("SELECT COUNT(*) FROM raw.transactions").fetchone()[0]
print(f"  ✓ raw.transactions: {count:,} rows")

# ── Amazon Catalog ────────────────────────────────────────────────────────────
print("\n[4/4] Loading Amazon catalog...")
conn.execute("""
    CREATE OR REPLACE TABLE raw.products AS
    SELECT * FROM read_parquet('data/processed/amazon_clean.parquet')
""")
count = conn.execute("SELECT COUNT(*) FROM raw.products").fetchone()[0]
print(f"  ✓ raw.products: {count:,} rows")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n=== DuckDB Raw Layer Summary ===")
tables = conn.execute("""
    SELECT table_name, estimated_size
    FROM duckdb_tables()
    WHERE schema_name = 'raw'
""").fetchall()
for t in tables:
    print(f"  raw.{t[0]}")

conn.close()
print("\n✓ All data loaded into DuckDB")
