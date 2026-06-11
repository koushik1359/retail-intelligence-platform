import numpy as np
import pandas as pd
import duckdb
import pickle
import os
import umap
from dotenv import load_dotenv

load_dotenv()
DUCKDB_PATH    = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
EMBEDDINGS_PATH = "models/recommendations/artifacts/item_embeddings.npy"
ENCODER_PATH    = "models/recommendations/artifacts/item_encoder.pkl"
OUT_PATH        = "data/processed/umap_item_embeddings.parquet"

print("Loading item embeddings...")
embeddings = np.load(EMBEDDINGS_PATH)
with open(ENCODER_PATH, "rb") as f:
    item_encoder = pickle.load(f)

# LabelEncoder stores original IDs in .classes_
product_ids = item_encoder.classes_
print(f"  {embeddings.shape[0]:,} items × {embeddings.shape[1]} dims")

print("Running UMAP (n_neighbors=15, min_dist=0.1)...")
reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, random_state=42, verbose=True)
coords  = reducer.fit_transform(embeddings)
print("UMAP done.")

con = duckdb.connect(DUCKDB_PATH, read_only=True)
products = con.execute("""
    SELECT product_id, product_name, department
    FROM main_mart.mart_recsys_interactions
    GROUP BY product_id, product_name, department
""").df()
con.close()

df = pd.DataFrame({
    "product_id": product_ids,
    "umap_x":     coords[:, 0],
    "umap_y":     coords[:, 1],
})
df = df.merge(products, on="product_id", how="left")

os.makedirs("data/processed", exist_ok=True)
df.to_parquet(OUT_PATH, index=False)
print(f"Saved {len(df):,} rows to {OUT_PATH}")
print(df.head())
