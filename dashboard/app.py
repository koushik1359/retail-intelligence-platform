import streamlit as st

st.set_page_config(
    page_title="Retail Intelligence Platform",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏪 Retail Intelligence Platform")
st.markdown("""
**End-to-end retail ML system** — demand forecasting, product recommendations,
real-time streaming, and AI-powered analytics.

Use the sidebar to navigate between modules.
""")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("dbt Models",   "12", "39 tests ✓")
col2.metric("Forecast RMSSE", "~0.58", "LightGBM Tweedie")
col3.metric("Rec Hit@10",   "0.36",  "ALS 64-dim")
col4.metric("Products RAG", "500",   "ChromaDB")
col5.metric("Agent Tools",  "5",     "Claude Opus 4.8")

st.divider()
st.info("Select a page from the sidebar to explore each module.")
