import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import inject_css, sidebar_brand, page_header, section, plotly_layout, badge, PRIMARY, MUTED, BORDER, TEAL, TEXT

st.set_page_config(page_title="Recommendations", layout="wide")
inject_css()
API = "https://koushik1359-retail-intelligence-api.hf.space"
UMAP_PATH = "data/processed/umap_item_embeddings.parquet"

@st.cache_data
def load_umap():
    try:    return pd.read_parquet(UMAP_PATH)
    except: return None

umap_df = load_umap()

with st.sidebar:
    sidebar_brand()
    st.page_link("app.py",                          label="Home",               icon="🏠")
    st.page_link("pages/1_Executive_overview.py",   label="Executive Overview", icon="📊")
    st.page_link("pages/2_Demand_Forecast.py",      label="Demand Forecast",    icon="📈")
    st.page_link("pages/3_Recommendations.py",      label="Recommendations",    icon="🛒")
    st.page_link("pages/4_Catalog_QA.py",           label="Catalog Q&A",        icon="💬")
    st.page_link("pages/5_Real_Time_Transactions.py", label="Live Transactions",icon="⚡")
    st.markdown("---")
    user_id = st.number_input("User ID", min_value=1, max_value=206209, value=1)
    n_recs  = st.slider("Recommendations", 5, 20, 10)
    run     = st.button("Get Recommendations", use_container_width=True)

page_header("Product Recommendations", "ALS 64-dim · FAISS retrieval · A/B hash routing")

DEPT_COLORS = {
    "snacks":    ("#EEF0FB","#3D52C4"),
    "beverages": ("#E0F5F5","#00696F"),
    "frozen":    ("#EDE9FE","#5B21B6"),
    "pantry":    ("#FFF7ED","#92400E"),
    "breakfast": ("#FEF3C7","#78350F"),
    "dairy eggs":("#D1FAE5","#065F46"),
    "produce":   ("#F0FDF4","#166534"),
    "meat seafood":("#FEE2E2","#991B1B"),
}

if run:
    with st.spinner("Fetching…"):
        r = requests.get(f"{API}/recommend", params={"user_id": user_id, "n": n_recs})
    if r.status_code == 200:
        data    = r.json()
        variant = data["variant"]
        items   = data["items"]
        rec_df  = pd.DataFrame(items)

        v_style = "indigo" if variant == "treatment" else "teal"
        st.markdown(
            f"<div style='margin-bottom:1.2rem;font-size:0.85rem;color:{MUTED}'>"
            f"User <strong>{user_id}</strong> assigned to "
            f"{badge(variant.title(), v_style)} variant</div>",
            unsafe_allow_html=True
        )

        col_l, col_r = st.columns([5, 7])

        with col_l:
            section("Recommended Products")
            for i, row in enumerate(items, 1):
                dept  = row.get("department","").lower()
                bg, fg = DEPT_COLORS.get(dept, ("#F6F6F7","#6D7175"))
                st.markdown(f"""
                <div style='display:flex;align-items:center;gap:12px;
                            padding:10px 12px;margin-bottom:5px;
                            background:{bg};border-radius:7px;
                            border:1px solid {BORDER}'>
                    <span style='font-size:0.75rem;font-weight:700;color:{fg};
                                 min-width:22px;text-align:center'>{i:02d}</span>
                    <div>
                        <div style='font-size:0.875rem;font-weight:600;color:{TEXT}'>{row["product_name"]}</div>
                        <div style='font-size:0.75rem;color:{MUTED};margin-top:1px'>{dept.title()}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col_r:
            section("Item Embedding Space (UMAP)")
            if umap_df is not None:
                rec_ids = set(rec_df["product_id"].tolist()) if "product_id" in rec_df.columns else set()
                sample  = umap_df.sample(n=6000, random_state=42)
                top     = pd.concat([
                    sample[sample["product_id"].isin(rec_ids)],
                    umap_df[umap_df["product_id"].isin(rec_ids)]
                ]).drop_duplicates()
                bg_pts = sample[~sample["product_id"].isin(rec_ids)]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=bg_pts["umap_x"], y=bg_pts["umap_y"],
                    mode="markers",
                    marker=dict(size=3, color="#D1D5DB", opacity=0.7),
                    name="All products", hoverinfo="skip",
                ))
                if not top.empty:
                    fig.add_trace(go.Scatter(
                        x=top["umap_x"], y=top["umap_y"],
                        mode="markers",
                        marker=dict(size=12, color=PRIMARY,
                                    line=dict(color="white", width=1.5),
                                    symbol="circle"),
                        text=top.get("product_name", pd.Series()).str[:22],
                        name="Recommended",
                        hovertemplate="<b>%{text}</b><extra></extra>",
                    ))
                plotly_layout(fig, height=400)
                fig.update_layout(showlegend=True,
                                  xaxis=dict(showticklabels=False, title="UMAP-1"),
                                  yaxis=dict(showticklabels=False, title="UMAP-2"))
                st.plotly_chart(fig, use_container_width=True)

    elif r.status_code == 404:
        st.warning(r.json()["detail"])
    else:
        st.error(f"API error {r.status_code}")

st.markdown("---")
section("A/B Test Results")
ab = requests.get(f"{API}/ab-test/results")
if ab.status_code == 200:
    data = ab.json()
    if isinstance(data, list) and data:
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.markdown(f"<p style='color:{MUTED};font-size:0.85rem'>No data yet.</p>", unsafe_allow_html=True)
