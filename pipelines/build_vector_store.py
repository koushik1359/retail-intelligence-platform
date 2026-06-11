import pandas as pd
import chromadb
import os
from sentence_transformers import SentenceTransformer

OUT_DIR    = "data/chromadb"
DESC_PATH  = "data/processed/product_descriptions.parquet"
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading product descriptions...")
df = pd.read_parquet(DESC_PATH)
print(f"Loaded {len(df):,} products")

print("Loading embedding model (all-MiniLM-L6-v2)...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Generating embeddings...")
texts = (df["product_name"] + " | " + df["department"] + " | " + df["description"]).tolist()
embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)

print("Building ChromaDB collection...")
client     = chromadb.PersistentClient(path=OUT_DIR)
try:
    client.delete_collection("product_catalog")
except Exception:
    pass

collection = client.create_collection(
    name="product_catalog",
    metadata={"hnsw:space": "cosine"},
)

collection.add(
    ids        = [str(pid) for pid in df["product_id"].tolist()],
    embeddings = embeddings.tolist(),
    documents  = texts,
    metadatas  = [
        {"product_id": int(r.product_id), "product_name": r.product_name,
         "department": r.department, "aisle": r.aisle}
        for r in df.itertuples()
    ],
)

print(f"\n✓ ChromaDB collection: {collection.count():,} products")
print(f"  Saved to {OUT_DIR}/")

# Sanity check
print("\nSemantic search test: 'healthy breakfast cereal'")
results = collection.query(query_texts=["healthy breakfast cereal"], n_results=5)
for name, dept in zip(
    [m["product_name"] for m in results["metadatas"][0]],
    [m["department"]   for m in results["metadatas"][0]],
):
    print(f"  → {name} ({dept})")
