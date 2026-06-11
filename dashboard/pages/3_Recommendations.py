import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Recommendations", layout="wide")
st.title("🛒 Product Recommendations")

API       = "http://localhost:8000"
UMAP_PATH = "data/processed/umap_item_embeddings.parquet"

@st.cache_data
def load_umap():
    try:
        return pd.read_parquet(UMAP_PATH)
    except FileNotFoundError:
        return None

umap_df = load_umap()

col1, col2 = st.columns([2, 1])
user_id = col1.number_input("User ID", min_value=1, max_value=206209, value=1, step=1)
n_recs  = col2.slider("Number of Recommendations", 5, 20, 10)

if st.button("Get Recommendations", type="primary"):
    with st.spinner("Fetching recommendations..."):
        r = requests.get(f"{API}/recommend", params={"user_id": user_id, "n": n_recs})

    if r.status_code == 200:
        data    = r.json()
        variant = data["variant"]
        items   = data["items"]

        badge = "🟢 Treatment" if variant == "treatment" else "🔵 Control"
        st.info(f"A/B Variant: **{badge}**")

        rec_df = pd.DataFrame(items)
        rec_df.index += 1

        col_left, col_right = st.columns([1, 2])

        with col_left:
            st.subheader("Recommended Products")
            st.dataframe(
                rec_df[["product_name", "department"]].rename(
                    columns={"product_name": "Product", "department": "Department"}
                ),
                use_container_width=True,
            )

        with col_right:
            st.subheader("Item Embedding Space (UMAP)")
            if umap_df is not None:
                rec_ids = set(rec_df["product_id"].tolist()) if "product_id" in rec_df.columns else set()

                sample = umap_df.sample(n=5000, random_state=42)
                sample["highlight"] = sample["product_id"].isin(rec_ids)

                bg  = sample[~sample["highlight"]]
                top = sample[sample["highlight"]]
                # also grab recommended items even if not in sample
                if rec_ids:
                    top = pd.concat([top, umap_df[umap_df["product_id"].isin(rec_ids)]]).drop_duplicates()

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=bg["umap_x"], y=bg["umap_y"],
                    mode="markers",
                    marker=dict(size=3, color="#CBD5E1", opacity=0.5),
                    name="All Products",
                    hoverinfo="skip",
                ))
                if not top.empty:
                    fig.add_trace(go.Scatter(
                        x=top["umap_x"], y=top["umap_y"],
                        mode="markers+text",
                        marker=dict(size=10, color="#EF4444", symbol="star"),
                        text=top["product_name"].str[:20] if "product_name" in top.columns else None,
                        textposition="top center",
                        name="Recommended",
                    ))
                fig.update_layout(
                    height=450,
                    xaxis_title="UMAP-1",
                    yaxis_title="UMAP-2",
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("UMAP file not found. Run `python models/recommendations/umap_projection.py` first.")

    elif r.status_code == 404:
        st.warning(r.json()["detail"])
    else:
        st.error(f"API error {r.status_code}")

st.divider()
st.subheader("📊 A/B Test Results")
ab = requests.get(f"{API}/ab-test/results")
if ab.status_code == 200:
    data = ab.json()
    if isinstance(data, list) and data:
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info(data.get("message", "No A/B test data yet — call /recommend a few times first.") if isinstance(data, dict) else "No data yet.")
