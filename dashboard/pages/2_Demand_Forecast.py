import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Demand Forecast", layout="wide")
st.title("📈 Demand Forecast")

API = "http://localhost:8000"

STORES = ["CA_1","CA_2","CA_3","CA_4","TX_1","TX_2","TX_3","WI_1","WI_2","WI_3"]
ITEMS  = ["FOODS_3_001","FOODS_3_002","FOODS_1_001","HOBBIES_1_001",
          "HOUSEHOLD_1_001","FOODS_2_001","HOBBIES_2_001","HOUSEHOLD_2_001"]

col1, col2, col3 = st.columns(3)
store_id = col1.selectbox("Store", STORES)
item_id  = col2.selectbox("Item",  ITEMS)
horizon  = col3.slider("Forecast Horizon (days)", 7, 56, 28)

if st.button("Generate Forecast", type="primary"):
    with st.spinner("Running LightGBM forecast..."):
        r = requests.get(f"{API}/forecast",
                         params={"store_id": store_id, "item_id": item_id, "horizon": horizon})
    if r.status_code == 200:
        data = r.json()
        df   = pd.DataFrame({"date": data["dates"], "forecast": data["forecast"]})
        df["date"] = pd.to_datetime(df["date"])

        st.metric("Total Forecast Units", f"{data['total_forecast_units']:.1f}",
                  f"over {horizon} days")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["date"], y=df["forecast"],
                                 mode="lines+markers", name="Forecast",
                                 line=dict(color="#2196F3", width=2)))
        fig.update_layout(title=f"28-Day Demand Forecast — {store_id} / {item_id}",
                          xaxis_title="Date", yaxis_title="Predicted Units")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df.rename(columns={"date": "Date", "forecast": "Predicted Units"}),
                     use_container_width=True)
    elif r.status_code == 404:
        st.warning(r.json()["detail"])
    else:
        st.error(f"API error {r.status_code}")
