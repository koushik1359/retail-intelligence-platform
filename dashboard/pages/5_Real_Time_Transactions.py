import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
from kafka import KafkaConsumer
import json

st.set_page_config(page_title="Real-Time Transactions", layout="wide")
st.title("⚡ Real-Time Transactions")
st.caption("Live feed from Kafka raw.transactions topic.")

BROKER = "localhost:9092"

col1, col2 = st.columns([3, 1])
max_msgs = col1.slider("Messages to fetch", 50, 500, 100)
refresh  = col2.button("🔄 Refresh Feed", type="primary")

if refresh or "txn_data" not in st.session_state:
    with st.spinner("Reading from Kafka..."):
        consumer = KafkaConsumer(
            "enriched.transactions",
            bootstrap_servers=[BROKER],
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            consumer_timeout_ms=3000,
            group_id=f"streamlit-{int(time.time())}",
        )
        msgs = []
        for msg in consumer:
            msgs.append(msg.value)
            if len(msgs) >= max_msgs:
                break
        consumer.close()
    st.session_state["txn_data"] = msgs

msgs = st.session_state.get("txn_data", [])

if not msgs:
    st.warning("No messages found. Make sure the producer and stream processor are running.")
    st.code("python pipelines/kafka/transaction_producer.py")
    st.stop()

df = pd.DataFrame(msgs)
st.success(f"Loaded {len(df):,} transactions from Kafka")

# ── KPI row ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Transactions",   f"{len(df):,}")
c2.metric("Total Revenue",  f"£{df['revenue'].sum():,.2f}")
c3.metric("Unique Products",f"{df['product_id'].nunique():,}")
c4.metric("Top Sellers",    f"{df['is_top_seller'].sum():,}" if "is_top_seller" in df.columns else "N/A")

# ── Revenue by country ─────────────────────────────────────────────────────────
if "country" in df.columns:
    fig = px.bar(
        df.groupby("country")["revenue"].sum().reset_index().sort_values("revenue", ascending=False).head(10),
        x="country", y="revenue", title="Revenue by Country (top 10)"
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Live feed table ────────────────────────────────────────────────────────────
st.subheader("Latest Transactions")
show_cols = [c for c in ["timestamp","txn_id","product_id","description","quantity","revenue","country"] if c in df.columns]
st.dataframe(df[show_cols].head(50), use_container_width=True)
