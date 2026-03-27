import streamlit as st
import json
import pandas as pd

st.set_page_config(layout="wide")

ASSETS = ["BANKNIFTY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK"]

st.title("⚡ LIVE FLOW DASHBOARD")

def load_data():
    try:
        with open("live_data.json") as f:
            return json.load(f)
    except:
        return {}

tabs = st.tabs(ASSETS)

data = load_data()

for i, asset in enumerate(ASSETS):
    with tabs[i]:

        if not data:
            st.warning("Waiting for live data...")
            continue

        df = pd.DataFrame(data).T

        st.subheader(asset)

        # Simple metrics (you will upgrade later)
        col1, col2, col3 = st.columns(3)

        col1.metric("Total OI", int(df["oi"].sum()))
        col2.metric("Total Volume", int(df["volume"].sum()))
        col3.metric("Avg Price", round(df["ltp"].mean(), 2))

        st.dataframe(df)
