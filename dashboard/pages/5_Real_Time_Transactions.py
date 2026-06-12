import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json, time
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import inject_css, sidebar_brand, page_header, section, plotly_layout, CHART_COLORS, PRIMARY, TEAL, MUTED, BORDER, TEXT

st.set_page_config(page_title="Live Transactions", layout="wide")
inject_css()

st.markdown("""
<style>
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.25} }
.live-badge {
    display:inline-flex;align-items:center;gap:6px;
    background:#D1FAE5;border:1px solid #6EE7B7;
    border-radius:20px;padding:3px 10px;
    font-size:0.75rem;font-weight:700;color:#065F46;
}
.live-dot { width:7px;height:7px;border-radius:50%;background:#059669;animation:blink 1.4s infinite; }
</style>
""", unsafe_allow_html=True)

BROKER = "localhost:9092"

with st.sidebar:
    sidebar_brand()
    st.page_link("app.py",                          label="Home",               icon="🏠")
    st.page_link("pages/1_Executive_overview.py",   label="Executive Overview", icon="📊")
    st.page_link("pages/2_Demand_Forecast.py",      label="Demand Forecast",    icon="📈")
    st.page_link("pages/3_Recommendations.py",      label="Recommendations",    icon="🛒")
    st.page_link("pages/4_Catalog_QA.py",           label="Catalog Q&A",        icon="💬")
    st.page_link("pages/5_Real_Time_Transactions.py", label="Live Transactions",icon="⚡")
    st.markdown("---")
    max_msgs = st.slider("Messages", 50, 500, 150)
    refresh  = st.button("Refresh Feed", use_container_width=True)
    st.markdown(f"<p style='font-size:0.75rem;color:{MUTED};margin-top:0.3rem'>Topic: enriched.transactions</p>",
                unsafe_allow_html=True)

page_header("Real-Time Transactions", "Live feed — Kafka enriched.transactions")
st.markdown('<div class="live-badge"><span class="live-dot"></span>LIVE</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

if refresh or "txn_data" not in st.session_state:
    with st.spinner("Reading from Kafka…"):
        try:
            from kafka import KafkaConsumer, TopicPartition
            consumer = KafkaConsumer(
                bootstrap_servers=[BROKER],
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                consumer_timeout_ms=3000,
            )
            tp = TopicPartition("enriched.transactions", 0)
            consumer.assign([tp])
            end_offset = consumer.end_offsets([tp])[tp]
            start_offset = max(0, end_offset - max_msgs)
            consumer.seek(tp, start_offset)
            msgs = []
            for msg in consumer:
                msgs.append(msg.value)
                if msg.offset >= end_offset - 1:
                    break
            consumer.close()
            st.session_state["txn_data"] = msgs
        except Exception as e:
            st.session_state["txn_data"] = []
            st.warning(f"Kafka not reachable: {e}")

msgs = st.session_state.get("txn_data", [])
if not msgs:
    st.markdown(f"<div style='text-align:center;padding:3rem;color:{MUTED}'>"
                "Start the producer and processor, then click Refresh.</div>",
                unsafe_allow_html=True)
    st.stop()

df = pd.DataFrame(msgs)
st.success(f"{len(df):,} transactions loaded")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Transactions",    f"{len(df):,}")
c2.metric("Total Revenue",   f"£{df['revenue'].sum():,.2f}")
c3.metric("Unique Products", f"{df['product_id'].nunique():,}")
top = int(df["is_top_seller"].sum()) if "is_top_seller" in df.columns else 0
c4.metric("Top-Seller Hits", f"{top:,}")

st.markdown("<br>", unsafe_allow_html=True)
col_l, col_r = st.columns([3, 2])

with col_l:
    if "country" in df.columns:
        top10 = (df.groupby("country")["revenue"].sum()
                   .sort_values(ascending=False).head(10).reset_index())
        fig = go.Figure(go.Bar(
            x=top10["country"], y=top10["revenue"],
            marker=dict(color=PRIMARY, opacity=0.82),
            hovertemplate="%{x}: £%{y:,.0f}<extra></extra>",
        ))
        plotly_layout(fig, "Revenue by Country", height=290)
        st.plotly_chart(fig, use_container_width=True)

with col_r:
    if "is_top_seller" in df.columns:
        counts = df["is_top_seller"].value_counts().reset_index()
        counts["label"] = counts["is_top_seller"].map({True: "Top Seller", False: "Standard"})
        fig2 = go.Figure(go.Pie(
            labels=counts["label"], values=counts["count"],
            marker_colors=[TEAL, "#E5E7EB"],
            hole=0.6, textinfo="percent+label",
            textfont=dict(size=11.5),
        ))
        plotly_layout(fig2, "Product Mix", height=290)
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

section("Recent Transactions")
show = [c for c in ["timestamp","product_id","description","quantity","revenue","country"] if c in df.columns]
st.dataframe(df[show].head(40), use_container_width=True, hide_index=True)
