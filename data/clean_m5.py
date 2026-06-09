import pandas as pd
import os

print("Cleaning M5 dataset...")

BASE = "data/raw/m5"
OUT  = "data/processed"
os.makedirs(OUT, exist_ok=True)

# Load
sales    = pd.read_csv(f"{BASE}/sales_train_evaluation.csv")
calendar = pd.read_csv(f"{BASE}/calendar.csv")
prices   = pd.read_csv(f"{BASE}/sell_prices.csv")

# ── Sales: wide → long ────────────────────────────────────────────────────────
id_cols  = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
day_cols = [c for c in sales.columns if c.startswith("d_")]
sales_long = sales.melt(id_vars=id_cols, value_vars=day_cols,
                        var_name="d", value_name="unit_sales")
sales_long["unit_sales"] = sales_long["unit_sales"].clip(lower=0).fillna(0).astype(int)

# ── Calendar: fix types, fill event nulls ─────────────────────────────────────
calendar["date"]         = pd.to_datetime(calendar["date"])
calendar["event_name_1"] = calendar["event_name_1"].fillna("None")
calendar["event_type_1"] = calendar["event_type_1"].fillna("None")
calendar["event_name_2"] = calendar["event_name_2"].fillna("None")
calendar["event_type_2"] = calendar["event_type_2"].fillna("None")
calendar = calendar[["date","wm_yr_wk","weekday","wday","month","year",
                      "d","event_name_1","event_type_1","snap_CA","snap_TX","snap_WI"]]

# ── Prices: already clean ─────────────────────────────────────────────────────
prices = prices[prices["sell_price"] > 0].dropna(subset=["sell_price"])

# ── Join ──────────────────────────────────────────────────────────────────────
df = sales_long.merge(calendar, on="d", how="left")
df = df.merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left")
df = df.dropna(subset=["sell_price"])
df = df.sort_values(["store_id", "item_id", "date"]).reset_index(drop=True)
df["revenue"] = df["unit_sales"] * df["sell_price"]

print(f"Final shape: {df.shape}")
print(f"Date range: {df['date'].min()} → {df['date'].max()}")
print(f"Missing values: {df.isnull().sum().sum()}")

df.to_parquet(f"{OUT}/m5_clean.parquet", index=False)
print(f"✓ Saved to {OUT}/m5_clean.parquet  ({os.path.getsize(f'{OUT}/m5_clean.parquet')/1e6:.1f} MB)")
