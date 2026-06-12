import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import inject_css, sidebar_brand, page_header, badge, section, PRIMARY, MUTED, BORDER, TEXT

st.set_page_config(
    page_title="Retail Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

with st.sidebar:
    sidebar_brand()
    st.markdown("**Navigate**")
    st.page_link("app.py",                          label="Home",                 icon="🏠")
    st.page_link("pages/1_Executive_overview.py",   label="Executive Overview",   icon="📊")
    st.page_link("pages/2_Demand_Forecast.py",      label="Demand Forecast",      icon="📈")
    st.page_link("pages/3_Recommendations.py",      label="Recommendations",      icon="🛒")
    st.page_link("pages/4_Catalog_QA.py",           label="Catalog Q&A",          icon="💬")
    st.page_link("pages/5_Real_Time_Transactions.py", label="Live Transactions",  icon="⚡")

page_header("Retail Intelligence Platform",
            "End-to-end ML system modelled on Walmart-scale retail operations")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("dbt Models",       "12",    "39 tests passing")
c2.metric("Forecast RMSSE",   "0.58",  "LightGBM Tweedie")
c3.metric("Rec Hit@10",       "0.36",  "ALS 64-dim")
c4.metric("Products in RAG",  "500",   "ChromaDB indexed")
c5.metric("Agent Tools",      "5",     "Claude Opus 4.8")

st.markdown("<br>", unsafe_allow_html=True)
col_l, col_r = st.columns(2)

def stack_row(name, desc, b_style):
    return (
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"padding:9px 0;border-bottom:1px solid {BORDER}'>"
        f"<span style='font-size:0.87rem;font-weight:600;color:{TEXT}'>{name}</span>"
        f"<span style='font-size:0.8rem;color:{MUTED}'>{desc}</span>"
        f"</div>"
    )

with col_l:
    section("Data & ML")
    rows = [
        ("M5 Walmart Sales",       "42,840 time series · 5 years"),
        ("Instacart Basket",       "3.4M orders · 200K users"),
        ("Online Retail II",       "805K UK transactions"),
        ("LightGBM Tweedie",       "3-fold CV · SHAP · MLflow"),
        ("ALS Recommendations",    "FAISS · UMAP 2D scatter"),
        ("Kafka Streaming",        "4 topics · 50 txns/sec"),
    ]
    for name, desc in rows:
        st.markdown(stack_row(name, desc, "indigo"), unsafe_allow_html=True)

with col_r:
    section("LLM & Serving")
    rows = [
        ("Claude Haiku 4.5",       "500-product catalog enrichment"),
        ("Claude Opus 4.8",        "RAG Q&A · executive summaries"),
        ("Autonomous Agent",       "5 tools · adaptive thinking"),
        ("FastAPI",                "8 endpoints · Prometheus metrics"),
        ("Streamlit",              "5 pages · A/B test display"),
        ("GitHub Actions CI",      "pytest · dbt test on push"),
    ]
    for name, desc in rows:
        st.markdown(stack_row(name, desc, "teal"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.info("Select a module from the sidebar to explore the platform.")
