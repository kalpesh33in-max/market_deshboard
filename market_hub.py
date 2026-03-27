import streamlit as st
import json
import time
import pandas as pd

st.set_page_config(layout="wide")

st.title("⚡ LIVE OPTIONS FLOW DASHBOARD")

def load_data():
    try:
        with open("live_data.json") as f:
            return json.load(f)
    except:
        return {}

while True:
    data = load_data()

    st.empty()

    if data:
        df = pd.DataFrame(data).T

        st.subheader("Live Market Data")

        st.dataframe(df)

    time.sleep(2)
    st.rerun()
