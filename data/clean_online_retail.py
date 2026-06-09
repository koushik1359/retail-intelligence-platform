import pandas as pd
import os

print("Cleaning Online Retail II dataset...")

BASE = "data/raw/online_retail"
OUT  = "data/processed"
os.makedirs(OUT, exist_ok=True)

# Load both sheets and combine
df1 = pd.read_excel(f"{BASE}/online_retail_II.xlsx", sheet_name="Year 2009-2010")
df2 = pd.read_excel(f"{BASE}/online_retail_II.xlsx", sheet_name="Year 2010-2011")
df  = pd.concat([df1, df2], ignore_index=True)
print(f"Raw shape: {df.shape}")

# ── Drop cancellations (Invoice starts with C) ────────────────────────────────
df = df[~df["Invoice"].astype(str).str.startswith("C")]

# ── Drop non-product StockCodes (keep only 5-digit numeric) ──────────────────
df = df[df["StockCode"].astype(str).str.match(r"^\d{5}$")]

# ── Drop bad quantities and prices ───────────────────────────────────────────
df = df[df["Quantity"] > 0]
df = df[df["Price"] > 0]

# ── Drop missing Customer ID and Description ──────────────────────────────────
df = df.dropna(subset=["Customer ID", "Description"])

# ── Fix types ─────────────────────────────────────────────────────────────────
df["Customer ID"]  = df["Customer ID"].astype(int)
df["InvoiceDate"]  = pd.to_datetime(df["InvoiceDate"])

# ── Rename to snake_case ──────────────────────────────────────────────────────
df = df.rename(columns={
    "Invoice":     "invoice_id",
    "StockCode":   "product_id",
    "Description": "description",
    "Quantity":    "quantity",
    "InvoiceDate": "invoice_date",
    "Price":       "unit_price",
    "Customer ID": "customer_id",
    "Country":     "country"
})

# ── Add revenue column ────────────────────────────────────────────────────────
df["revenue"] = df["quantity"] * df["unit_price"]

# ── Sort by date (important for Kafka producer replay) ───────────────────────
df = df.sort_values("invoice_date").reset_index(drop=True)

print(f"Clean shape: {df.shape}")
print(f"Rows dropped: {1067371 - len(df):,} ({(1 - len(df)/1067371)*100:.1f}%)")
print(f"Date range: {df['invoice_date'].min()} → {df['invoice_date'].max()}")
print(f"Unique customers: {df['customer_id'].nunique():,}")
print(f"Unique products: {df['product_id'].nunique():,}")
print(f"Missing values: {df.isnull().sum().sum()}")
print(f"Revenue stats:\n{df['revenue'].describe().round(2)}")

df.to_parquet(f"{OUT}/online_retail_clean.parquet", index=False)
print(f"✓ Saved to {OUT}/online_retail_clean.parquet  ({os.path.getsize(f'{OUT}/online_retail_clean.parquet')/1e6:.1f} MB)")
