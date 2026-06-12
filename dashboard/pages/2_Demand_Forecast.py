import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import inject_css, sidebar_brand, page_header, section, plotly_layout, PRIMARY, MUTED, BORDER

st.set_page_config(page_title="Demand Forecast", layout="wide")
inject_css()
API = "https://koushik1359-retail-intelligence-api.hf.space"
STORES = ["CA_1","CA_2","CA_3","CA_4","TX_1","TX_2","TX_3","WI_1","WI_2","WI_3"]
ITEMS  = ["FOODS_3_001","FOODS_3_002","FOODS_1_001","HOBBIES_1_001",
          "HOUSEHOLD_1_001","FOODS_2_001","HOBBIES_2_001","HOUSEHOLD_2_001"]

with st.sidebar:
    sidebar_brand()
    st.page_link("app.py",                          label="Home",               icon="🏠")
    st.page_link("pages/1_Executive_overview.py",   label="Executive Overview", icon="📊")
    st.page_link("pages/2_Demand_Forecast.py",      label="Demand Forecast",    icon="📈")
    st.page_link("pages/3_Recommendations.py",      label="Recommendations",    icon="🛒")
    st.page_link("pages/4_Catalog_QA.py",           label="Catalog Q&A",        icon="💬")
    st.page_link("pages/5_Real_Time_Transactions.py", label="Live Transactions",icon="⚡")
    st.markdown("---")
    store_id = st.selectbox("Store", STORES)
    item_id  = st.selectbox("Item",  ITEMS)
    horizon  = st.slider("Horizon (days)", 7, 56, 28)
    run      = st.button("Generate Forecast", use_container_width=True)

page_header("Demand Forecast", "LightGBM Tweedie · 3-fold time-series CV · MLflow tracked")

if run:
    with st.spinner("Running model…"):
        r = requests.get(f"{API}/forecast",
                         params={"store_id": store_id, "item_id": item_id, "horizon": horizon})
    if r.status_code == 200:
        data = r.json()
        df   = pd.DataFrame({"date": pd.to_datetime(data["dates"]), "units": data["forecast"]})

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Forecast",  f"{data['total_forecast_units']:.1f} units")
        c2.metric("Daily Average",   f"{data['total_forecast_units']/horizon:.2f} units/day")
        c3.metric("Store · Item",    f"{store_id}  ·  {item_id}")

        st.markdown("<br>", unsafe_allow_html=True)

        avg = data["total_forecast_units"] / horizon
        fig = go.Figure()
        fig.add_hrect(y0=avg*0.8, y1=avg*1.2,
                      fillcolor="rgba(99,102,241,0.05)",
                      line_width=0, name="±20% band")
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["units"],
            mode="lines+markers",
            line=dict(color=PRIMARY, width=2.2),
            marker=dict(size=4.5, color=PRIMARY),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.07)",
            name="Forecast",
            hovertemplate="%{x|%a %b %d}: %{y:.2f} units<extra></extra>",
        ))
        fig.add_hline(y=avg, line_dash="dot",
                      line=dict(color=MUTED, width=1.2),
                      annotation_text=f"Avg {avg:.2f}",
                      annotation_font=dict(size=11, color=MUTED))
        plotly_layout(fig, f"{store_id} · {item_id} — {horizon}-day demand forecast", height=380)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Forecast table"):
            st.dataframe(
                df.assign(date=df["date"].dt.strftime("%Y-%m-%d"))
                  .rename(columns={"date": "Date", "units": "Forecast (units)"}),
                use_container_width=True, hide_index=True,
            )
    elif r.status_code == 404:
        st.warning(r.json()["detail"])
    else:
        st.error(f"API error {r.status_code}")
else:
    st.markdown(
        f"<div style='text-align:center;padding:5rem 0;color:{MUTED};font-size:0.9rem'>"
        "Choose a store and item in the sidebar, then click Generate Forecast.</div>",
        unsafe_allow_html=True
    )
