import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Executive Overview", layout="wide")
st.title("📊 Executive Overview")

API = "http://localhost:8000"

@st.cache_data(ttl=60)
def get_kpis(days=30):
    r = requests.get(f"{API}/kpis?days={days}")
    return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()

@st.cache_data(ttl=300)
def get_reports():
    r = requests.get(f"{API}/agent/reports?limit=3")
    return r.json() if r.status_code == 200 else []

df = get_kpis(30)

if df.empty:
    st.warning("API not reachable. Make sure FastAPI is running on port 8000.")
    st.stop()

df["kpi_date"] = pd.to_datetime(df["kpi_date"])
latest = df.iloc[0]

# ── KPI cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue (latest day)",  f"£{latest['total_revenue']:,.0f}",
          f"{latest.get('revenue_wow_pct', 0):+.1f}% WoW")
c2.metric("Orders",                f"{latest['total_orders']:,}")
c3.metric("Unique Customers",      f"{latest['unique_customers']:,}")
c4.metric("Avg Basket Size",       f"£{latest['avg_basket_size']:,.2f}")

st.divider()

# ── Revenue trend ──────────────────────────────────────────────────────────────
fig = px.line(df.sort_values("kpi_date"), x="kpi_date", y="total_revenue",
              title="Daily Revenue (last 30 days)", markers=True)
spike_days = df[df["is_revenue_spike"] == True]
if not spike_days.empty:
    fig.add_scatter(x=spike_days["kpi_date"], y=spike_days["total_revenue"],
                    mode="markers", marker=dict(color="red", size=10, symbol="star"),
                    name="Revenue Spike")
st.plotly_chart(fig, use_container_width=True)

col_l, col_r = st.columns(2)

with col_l:
    fig2 = px.bar(df.sort_values("kpi_date").tail(14),
                  x="kpi_date", y="total_orders", title="Daily Orders (last 14 days)")
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    fig3 = px.line(df.sort_values("kpi_date"), x="kpi_date", y="avg_basket_size",
                   title="Avg Basket Size Trend")
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Latest agent report ────────────────────────────────────────────────────────
st.subheader("🤖 Latest AI Agent Report")
reports = get_reports()
if reports:
    r = reports[0]
    st.caption(f"Generated: {r.get('created_at') or r.get('timestamp', 'N/A')}")
    st.markdown(r["report"])
else:
    if st.button("Run Monitoring Agent"):
        with st.spinner("Agent running... (30-60 seconds)"):
            resp = requests.get(f"{API}/agent/run")
            if resp.status_code == 200:
                st.success("Report generated!")
                st.markdown(resp.json()["report"])
            else:
                st.error("Agent failed.")
