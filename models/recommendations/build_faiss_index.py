import numpy as np
import faiss
import pickle
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
OUT_DIR     = "models/recommendations/artifacts"

# ── Load ALS item embeddings (saved directly by train_recommender.py) ──────────
print("Loading item embeddings...")
item_embeddings = np.load(f"{OUT_DIR}/item_embeddings.npy").astype(np.float32)
print(f"Embeddings shape: {item_embeddings.shape}")

with open(f"{OUT_DIR}/item_encoder.pkl", "rb") as f:
    item_enc = pickle.load(f)

# ── Build FAISS index (Inner Product over L2-normalized vectors = cosine sim) ──
print("Building FAISS IndexFlatIP...")
norms = np.linalg.norm(item_embeddings, axis=1, keepdims=True)
item_embeddings_norm = item_embeddings / np.clip(norms, 1e-8, None)

d     = item_embeddings_norm.shape[1]
index = faiss.IndexFlatIP(d)
index.add(item_embeddings_norm)
faiss.write_index(index, f"{OUT_DIR}/item_index.faiss")

# Save normalized embeddings too (used by the API for user-side retrieval)
np.save(f"{OUT_DIR}/item_embeddings_norm.npy", item_embeddings_norm)

print(f"✓ FAISS index: {index.ntotal:,} items  dim={d}")
print(f"  Saved to {OUT_DIR}/item_index.faiss")

# ── Sanity check: top-10 similar items for a random product ───────────────────
con = duckdb.connect(DUCKDB_PATH, read_only=True)
products = con.execute("""
    SELECT DISTINCT product_id, product_name
    FROM main_intermediate.int_user_product_interactions
""").df().set_index("product_id")
con.close()

query_idx = 100
query_emb = item_embeddings_norm[[query_idx]]
_, I      = index.search(query_emb, 11)
orig_ids  = item_enc.inverse_transform(I[0])
query_pid = orig_ids[0]

print(f"\nTop-10 similar to: '{products['product_name'].get(query_pid, query_pid)}'")
for rank, pid in enumerate(orig_ids[1:], 1):
    print(f"  {rank:2d}. {products['product_name'].get(pid, pid)}")
