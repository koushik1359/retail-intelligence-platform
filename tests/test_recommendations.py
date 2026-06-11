import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.integration
def test_umap_parquet_exists():
    assert os.path.exists("data/processed/umap_item_embeddings.parquet")


@pytest.mark.integration
def test_umap_shape():
    import pandas as pd
    df = pd.read_parquet("data/processed/umap_item_embeddings.parquet")
    assert "umap_x" in df.columns
    assert "umap_y" in df.columns
    assert "product_id" in df.columns
    assert len(df) > 10000


@pytest.mark.integration
def test_item_embeddings_exist():
    assert os.path.exists("models/recommendations/artifacts/item_embeddings.npy")
    assert os.path.exists("models/recommendations/artifacts/item_embeddings_norm.npy")


@pytest.mark.integration
def test_item_embeddings_shape():
    emb = np.load("models/recommendations/artifacts/item_embeddings.npy")
    assert emb.ndim == 2
    assert emb.shape[1] == 64


@pytest.mark.integration
def test_faiss_index_exists():
    assert os.path.exists("models/recommendations/artifacts/item_index.faiss")


def test_ab_routing_deterministic():
    def get_variant(user_id):
        return "treatment" if hash(str(user_id)) % 100 >= 50 else "control"

    for user_id in [1, 42, 100, 999, 12345]:
        v1 = get_variant(user_id)
        v2 = get_variant(user_id)
        assert v1 == v2, f"Non-deterministic variant for user {user_id}"


def test_ab_routing_distribution():
    def get_variant(user_id):
        return "treatment" if hash(str(user_id)) % 100 >= 50 else "control"

    variants = [get_variant(i) for i in range(10000)]
    treatment_pct = variants.count("treatment") / len(variants)
    assert 0.45 < treatment_pct < 0.55, f"A/B split skewed: {treatment_pct:.2%} treatment"
