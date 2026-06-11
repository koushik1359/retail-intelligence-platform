import duckdb
import anthropic
import pandas as pd
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
OUT_PATH    = "data/processed/product_descriptions.parquet"
BATCH_SIZE  = 10   # products per API call

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Load unique products ───────────────────────────────────────────────────────
print("Loading products from DuckDB...")
con = duckdb.connect(DUCKDB_PATH, read_only=True)
products = con.execute("""
    SELECT DISTINCT product_id, product_name, department, aisle
    FROM main_intermediate.int_user_product_interactions
    ORDER BY product_id
    LIMIT 500
""").df()
con.close()
print(f"Loaded {len(products):,} products")

# ── Enrichment function ────────────────────────────────────────────────────────
def enrich_batch(batch_df):
    """Send a batch of products to Claude Haiku and get descriptions back."""
    product_list = "\n".join([
        f"{i+1}. Name: {row.product_name} | Department: {row.department} | Aisle: {row.aisle}"
        for i, row in enumerate(batch_df.itertuples())
    ])

    prompt = f"""You are a retail product copywriter. For each product below, write a 2-sentence description suitable for an e-commerce product page. Be specific, factual, and helpful to shoppers.

Products:
{product_list}

Respond with a JSON array of objects, one per product, in this exact format:
[
  {{"id": 1, "description": "..."}},
  {{"id": 2, "description": "..."}}
]
Only output the JSON array, nothing else."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


# ── Process in batches ─────────────────────────────────────────────────────────
all_descriptions = []
total_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE

print(f"\nEnriching {len(products)} products in {total_batches} batches of {BATCH_SIZE}...")

for batch_num in range(total_batches):
    start = batch_num * BATCH_SIZE
    end   = min(start + BATCH_SIZE, len(products))
    batch = products.iloc[start:end]

    try:
        results = enrich_batch(batch)
        for item in results:
            idx = item["id"] - 1
            row = batch.iloc[idx]
            all_descriptions.append({
                "product_id":   int(row.product_id),
                "product_name": row.product_name,
                "department":   row.department,
                "aisle":        row.aisle,
                "description":  item["description"],
            })
        print(f"  Batch {batch_num+1}/{total_batches} done — {len(all_descriptions)} products enriched")
    except Exception as e:
        print(f"  Batch {batch_num+1} failed: {type(e).__name__}: {e}")

    time.sleep(0.3)  # stay under rate limits

# ── Save ───────────────────────────────────────────────────────────────────────
out_df = pd.DataFrame(all_descriptions)
out_df.to_parquet(OUT_PATH, index=False)

print(f"\n✓ Saved {len(out_df):,} descriptions to {OUT_PATH}")
print("\nSample:")
print(out_df[["product_name", "description"]].head(3).to_string(index=False))
