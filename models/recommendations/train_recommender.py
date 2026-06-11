import duckdb
import numpy as np
from scipy.sparse import csr_matrix
import implicit
from sklearn.preprocessing import LabelEncoder
import mlflow
import os
import pickle
import torch
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
MLFLOW_URI  = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
OUT_DIR     = "models/recommendations/artifacts"
os.makedirs(OUT_DIR, exist_ok=True)

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("recommendation_model")

# ── Load data ──────────────────────────────────────────────────────────────────
print("Loading interactions from DuckDB...")
con = duckdb.connect(DUCKDB_PATH, read_only=True)
df = con.execute("""
    SELECT user_id, product_id, interaction_score
    FROM main_intermediate.int_user_product_interactions
    WHERE interaction_score > 0
""").df()
con.close()
print(f"Loaded {len(df):,} interactions | {df['user_id'].nunique():,} users | {df['product_id'].nunique():,} items")

# ── Encode IDs ─────────────────────────────────────────────────────────────────
user_enc = LabelEncoder()
item_enc = LabelEncoder()
df["user_idx"] = user_enc.fit_transform(df["user_id"])
df["item_idx"] = item_enc.fit_transform(df["product_id"])
n_users = int(df["user_idx"].max() + 1)
n_items = int(df["item_idx"].max() + 1)
print(f"Encoded: {n_users:,} users, {n_items:,} items")

with open(f"{OUT_DIR}/user_encoder.pkl", "wb") as f: pickle.dump(user_enc, f)
with open(f"{OUT_DIR}/item_encoder.pkl", "wb") as f: pickle.dump(item_enc, f)

# ── Sparse interaction matrix ──────────────────────────────────────────────────
print("Building sparse interaction matrix...")
user_item = csr_matrix(
    (df["interaction_score"].values.astype(np.float32),
     (df["user_idx"].values, df["item_idx"].values)),
    shape=(n_users, n_items),
)
print(f"Matrix: {user_item.shape}  nnz: {user_item.nnz:,}")

# ── Evaluation setup (leave-one-out on top item per user) ─────────────────────
print("Precomputing evaluation set...")
top_items = (df.sort_values("interaction_score", ascending=False)
               .groupby("user_idx")["item_idx"].first().to_dict())

np.random.seed(42)
user_counts = df.groupby("user_idx").size()
eligible    = user_counts[user_counts >= 2].index.tolist()
val_users   = np.random.choice(eligible, size=min(500, len(eligible)), replace=False)


def evaluate(model, label=""):
    hits = 0; n = 0
    for uid in val_users:
        held_out = top_items.get(uid)
        if held_out is None: continue
        masked = user_item[uid].copy()
        masked[0, held_out] = 0
        masked.eliminate_zeros()
        recs = model.recommend(uid, masked, N=10, filter_already_liked_items=False)
        hits += int(held_out in set(recs[0].tolist()))
        n += 1
    hit10 = hits / n if n else 0.0
    print(f"  {label}Hit@10 = {hit10:.4f}  ({hits}/{n} users)")
    return hit10


# ══════════════════════════════════════════════════════════════════════════════
# ALS  (factors=64, iterations=50)
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== ALS (factors=64, iterations=50) ===")
with mlflow.start_run(run_name="als_64_50"):
    als = implicit.als.AlternatingLeastSquares(
        factors=64, regularization=0.01, iterations=50,
        calculate_training_loss=True, random_state=42, num_threads=0,
    )
    als.fit(user_item)
    hit10_als = evaluate(als, "ALS  ")
    mlflow.log_params({"algorithm": "ALS", "factors": 64,
                       "iterations": 50, "reg": 0.01})
    mlflow.log_metric("val_hit10", hit10_als)


# ══════════════════════════════════════════════════════════════════════════════
# Save model
# ══════════════════════════════════════════════════════════════════════════════
user_emb = als.user_factors.astype(np.float32)
item_emb = als.item_factors.astype(np.float32)

np.save(f"{OUT_DIR}/user_embeddings.npy", user_emb)
np.save(f"{OUT_DIR}/item_embeddings.npy", item_emb)
torch.save({"n_users": n_users, "n_items": n_items,
            "factors": 64, "best_model": "ALS"},
           f"{OUT_DIR}/model_config.pt")

print(f"\n✓ Saved ALS embeddings to {OUT_DIR}/")
print(f"  user_embeddings.npy  shape={user_emb.shape}")
print(f"  item_embeddings.npy  shape={item_emb.shape}")
print("→ Run build_faiss_index.py next")
