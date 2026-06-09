import pandas as pd
import os

print("Cleaning Instacart dataset...")

BASE = "data/raw/instacart"
OUT  = "data/processed"
os.makedirs(OUT, exist_ok=True)

# Load
orders      = pd.read_csv(f"{BASE}/orders.csv")
prior       = pd.read_csv(f"{BASE}/order_products__prior.csv")
train       = pd.read_csv(f"{BASE}/order_products__train.csv")
products    = pd.read_csv(f"{BASE}/products.csv")
aisles      = pd.read_csv(f"{BASE}/aisles.csv")
departments = pd.read_csv(f"{BASE}/departments.csv")

# ── Orders: fix nulls, drop test set ─────────────────────────────────────────
orders["days_since_prior_order"] = orders["days_since_prior_order"].fillna(0).astype(int)
orders = orders[orders["eval_set"] != "test"].reset_index(drop=True)

# ── Combine prior + train interactions ────────────────────────────────────────
interactions = pd.concat([prior, train], ignore_index=True)

# ── Join orders + interactions ────────────────────────────────────────────────
df = interactions.merge(orders[["order_id","user_id","order_number",
                                 "order_dow","order_hour_of_day",
                                 "days_since_prior_order"]], on="order_id", how="left")

# ── Join products + aisles + departments ──────────────────────────────────────
products = products.merge(aisles,      on="aisle_id",      how="left")
products = products.merge(departments, on="department_id", how="left")
df = df.merge(products, on="product_id", how="left")

# ── Filter users with < 3 orders (not enough history for recommendations) ─────
order_counts = df.groupby("user_id")["order_id"].nunique()
valid_users  = order_counts[order_counts >= 3].index
df = df[df["user_id"].isin(valid_users)].reset_index(drop=True)

print(f"Final shape: {df.shape}")
print(f"Unique users: {df['user_id'].nunique():,}")
print(f"Unique products: {df['product_id'].nunique():,}")
print(f"Unique orders: {df['order_id'].nunique():,}")
print(f"Missing values: {df.isnull().sum().sum()}")
print(f"Reorder rate: {df['reordered'].mean():.3f}")

df.to_parquet(f"{OUT}/instacart_clean.parquet", index=False)
print(f"✓ Saved to {OUT}/instacart_clean.parquet  ({os.path.getsize(f'{OUT}/instacart_clean.parquet')/1e6:.1f} MB)")
