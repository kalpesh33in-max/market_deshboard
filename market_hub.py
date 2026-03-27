import streamlit as st
import pandas as pd
import re
import os
from bs4 import BeautifulSoup

DATA_FILE = "raw_data.html"
ASSETS = ["BANKNIFTY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK"]

st.set_page_config(layout="wide")

# ---------- PARSE TELEGRAM DATA ----------
def parse_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    rows = []

    for msg in soup.find_all("div", class_="text"):
        text = msg.get_text()

        sym = re.search(r"Symbol: ([\w:]+)", text)
        lots = re.search(r"LOTS: ([\d,]+)", text)
        price = re.search(r"FUTURE PRICE: ([\d.]+)", text)

        if sym and lots:
            symbol = sym.group(1).replace("NFO:", "")
            base = next((a for a in ASSETS if symbol.startswith(a)), None)

            strike_match = re.search(r"(\d+)(CE|PE)", symbol)
            strike = int(strike_match.group(1)) if strike_match else 0
            typ = strike_match.group(2) if strike_match else "FUT"

            lots_val = int(lots.group(1).replace(",", ""))

            rows.append({
                "Base": base,
                "Strike": strike,
                "Type": typ,
                "Lots": lots_val,
                "Price": float(price.group(1)) if price else 0
            })

    return pd.DataFrame(rows)


df = parse_data()

st.title("⚡ PRO OPTIONS FLOW DASHBOARD")

tabs = st.tabs(ASSETS)

# ---------- DASHBOARD ----------
for i, asset in enumerate(ASSETS):
    with tabs[i]:
        d = df[df["Base"] == asset]

        if d.empty:
            st.warning("No Data")
            continue

        # Latest price
        ltp = d["Price"].iloc[-1]

        st.subheader(f"{asset}  |  LTP: {ltp}")

        # FLOW CALCULATION
        ce = d[d["Type"] == "CE"]["Lots"].sum()
        pe = d[d["Type"] == "PE"]["Lots"].sum()

        bullish = pe - ce
        bearish = ce - pe

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("CALL WRITING", f"{ce:,}")
        c2.metric("PUT WRITING", f"{pe:,}")
        c3.metric("BULLISH FLOW", f"{bullish:,}")
        c4.metric("BEARISH FLOW", f"{bearish:,}")

        st.markdown("---")

        # ---------- HEATMAP TABLE ----------
        strikes = sorted(d["Strike"].unique())

        table = []
        for s in strikes:
            ce_val = d[(d["Strike"] == s) & (d["Type"] == "CE")]["Lots"].sum()
            pe_val = d[(d["Strike"] == s) & (d["Type"] == "PE")]["Lots"].sum()

            table.append({
                "Strike": s,
                "CE": ce_val,
                "PE": pe_val
            })

        tdf = pd.DataFrame(table)

        def color(val):
            if val > 200:
                return "background-color: green"
            elif val < -200:
                return "background-color: red"
            return ""

        st.dataframe(tdf.style.applymap(color))
