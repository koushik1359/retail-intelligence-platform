import pandas as pd
import os

print("Cleaning Amazon catalog dataset...")

BASE = "data/raw/amazon_catalog"
OUT  = "data/processed"
os.makedirs(OUT, exist_ok=True)

# Load main catalog
df = pd.read_csv(f"{BASE}/Amazon-Products.csv", on_bad_lines="skip")
print(f"Raw shape: {df.shape}")

# ── Drop unneeded columns ─────────────────────────────────────────────────────
df = df.drop(columns=["Unnamed: 0", "image", "link"])

# ── Clean price columns (strip ₹ and commas → float) ─────────────────────────
def clean_price(series):
    return (series.astype(str)
                  .str.replace("₹", "", regex=False)
                  .str.replace(",", "", regex=False)
                  .str.strip()
                  .replace("nan", None)
                  .pipe(pd.to_numeric, errors="coerce"))

df["actual_price"]   = clean_price(df["actual_price"])
df["discount_price"] = clean_price(df["discount_price"])

# ── Clean ratings (→ float) ───────────────────────────────────────────────────
df["ratings"] = pd.to_numeric(df["ratings"], errors="coerce")

# ── Clean no_of_ratings (strip commas → int) ─────────────────────────────────
df["no_of_ratings"] = (df["no_of_ratings"].astype(str)
                                          .str.replace(",", "", regex=False)
                                          .pipe(pd.to_numeric, errors="coerce")
                                          .fillna(0).astype(int))

# ── Drop rows with no product name ───────────────────────────────────────────
df = df.dropna(subset=["name"])

# ── Add discount percentage where both prices exist ──────────────────────────
mask = df["actual_price"].notna() & df["discount_price"].notna() & (df["actual_price"] > 0)
df.loc[mask, "discount_pct"] = (
    (df.loc[mask, "actual_price"] - df.loc[mask, "discount_price"])
    / df.loc[mask, "actual_price"] * 100
).round(1)

# ── Add product_id column (for joining later) ─────────────────────────────────
df = df.reset_index(drop=True)
df.insert(0, "product_id", "AMZN_" + df.index.astype(str).str.zfill(6))

# ── Rename columns ────────────────────────────────────────────────────────────
df = df.rename(columns={
    "name":           "product_name",
    "main_category":  "category",
    "sub_category":   "sub_category",
    "ratings":        "avg_rating",
    "no_of_ratings":  "rating_count",
    "discount_price": "sale_price",
    "actual_price":   "list_price"
})

print(f"Clean shape: {df.shape}")
print(f"Missing values:\n{df.isnull().sum()}")
print(f"\nSample product:\n{df.iloc[0][['product_id','product_name','category','list_price','avg_rating']]}")

df.to_parquet(f"{OUT}/amazon_clean.parquet", index=False)
print(f"\n✓ Saved to {OUT}/amazon_clean.parquet  ({os.path.getsize(f'{OUT}/amazon_clean.parquet')/1e6:.1f} MB)")
