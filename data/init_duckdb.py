import duckdb
import os

print("Initializing DuckDB warehouse...")

os.makedirs("data", exist_ok=True)
conn = duckdb.connect("data/warehouse.duckdb")

# ── Create three-layer schema ─────────────────────────────────────────────────
conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
conn.execute("CREATE SCHEMA IF NOT EXISTS mart")

print("Schemas created: raw, staging, mart")

# ── Verify ────────────────────────────────────────────────────────────────────
schemas = conn.execute("SELECT schema_name FROM information_schema.schemata").fetchall()
print("Schemas in warehouse:", [s[0] for s in schemas])

conn.close()
print("DuckDB warehouse initialized at data/warehouse.duckdb")
