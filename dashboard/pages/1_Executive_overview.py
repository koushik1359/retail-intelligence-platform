import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import inject_css, sidebar_brand, page_header, section, plotly_layout, CHART_COLORS, PRIMARY, MUTED, BORDER, TEAL, AMBER

st.set_page_config(page_title="Executive Overview", layout="wide")
inject_css()
API = "http://localhost:8000"

@st.cache_data(ttl=60)
def get_kpis(days=30):
    r = requests.get(f"{API}/kpis?days={days}")
    return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()

@st.cache_data(ttl=300)
def get_reports():
    r = requests.get(f"{API}/agent/reports?limit=3")
    return r.json() if r.status_code == 200 else []

with st.sidebar:
    sidebar_brand()
    st.page_link("app.py",                          label="Home",               icon="🏠")
    st.page_link("pages/1_Executive_overview.py",   label="Executive Overview", icon="📊")
    st.page_link("pages/2_Demand_Forecast.py",      label="Demand Forecast",    icon="📈")
    st.page_link("pages/3_Recommendations.py",      label="Recommendations",    icon="🛒")
    st.page_link("pages/4_Catalog_QA.py",           label="Catalog Q&A",        icon="💬")
    st.page_link("pages/5_Real_Time_Transactions.py", label="Live Transactions",icon="⚡")
    st.markdown("---")
    st.markdown("**Settings**")
    days = st.slider("Lookback (days)", 7, 90, 30)

page_header("Executive Overview", "UK retail performance · Online Retail II dataset")

df = get_kpis(days)
if df.empty:
    st.warning("API not reachable — start FastAPI on port 8000.")
    st.stop()

df["kpi_date"] = pd.to_datetime(df["kpi_date"])
df = df.sort_values("kpi_date")
latest = df.iloc[-1]
prev   = df.iloc[-2] if len(df) > 1 else latest

def delta(a, b):
    return f"{((a-b)/b*100):+.1f}%" if b else ""

c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue",      f"£{latest['total_revenue']:,.0f}",   delta(latest['total_revenue'],    prev['total_revenue']))
c2.metric("Orders",       f"{latest['total_orders']:,}",         delta(latest['total_orders'],     prev['total_orders']))
c3.metric("Customers",    f"{latest['unique_customers']:,}",     delta(latest['unique_customers'], prev['unique_customers']))
c4.metric("Avg Basket",   f"£{latest['avg_basket_size']:.2f}",  delta(latest['avg_basket_size'],  prev['avg_basket_size']))

st.markdown("<br>", unsafe_allow_html=True)
col_l, col_r = st.columns([3, 2])

with col_l:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["kpi_date"], y=df["total_revenue"],
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.08)",
        line=dict(color=PRIMARY, width=2),
        name="Revenue",
        hovertemplate="£%{y:,.0f}<extra></extra>",
    ))
    spikes = df[df["is_revenue_spike"] == True]
    if not spikes.empty:
        fig.add_trace(go.Scatter(
            x=spikes["kpi_date"], y=spikes["total_revenue"],
            mode="markers",
            marker=dict(color="#D72C0D", size=8, symbol="diamond"),
            name="Spike",
            hovertemplate="Spike £%{y:,.0f}<extra></extra>",
        ))
    plotly_layout(fig, "Daily Revenue", height=270)
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    fig2 = go.Figure(go.Bar(
        x=df.tail(14)["kpi_date"],
        y=df.tail(14)["total_orders"],
        marker=dict(color=TEAL, opacity=0.8),
        hovertemplate="%{y:,} orders<extra></extra>",
    ))
    plotly_layout(fig2, "Daily Orders — last 14 days", height=270)
    st.plotly_chart(fig2, use_container_width=True)

fig3 = go.Figure(go.Scatter(
    x=df["kpi_date"], y=df["avg_basket_size"],
    mode="lines",
    line=dict(color=AMBER, width=1.8),
    hovertemplate="£%{y:.2f}<extra></extra>",
))
plotly_layout(fig3, "Avg Basket Size", height=200)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
section("Latest AI Agent Report")
reports = get_reports()
if reports:
    r = reports[0]
    ts = r.get("created_at") or r.get("timestamp", "")
    st.caption(f"Generated {ts}")
    st.markdown(r["report"])
else:
    if st.button("Run Monitoring Agent"):
        with st.spinner("Agent running… (30–60 s)"):
            resp = requests.get(f"{API}/agent/run")
            if resp.status_code == 200:
                st.success("Done.")
                st.markdown(resp.json()["report"])
            else:
                st.error("Agent failed.")
