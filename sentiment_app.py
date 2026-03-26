
import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup
import os
import json

st.set_page_config(page_title="Institutional Order Flow + LIVE Zerodha", layout="wide")

# Look for data files
DATA_FILE = "raw_data.html"
LIVE_DATA_FILE = "live_data.json"

# List of assets to identify in symbols
ASSETS = ["BANKNIFTY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "CRUDEOIL", "CRUDEOILM"]

def parse_html_data(file_path):
    if not os.path.exists(file_path): return pd.DataFrame()
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    messages = []
    for msg in soup.find_all('div', class_='text'):
        text = msg.get_text(separator="\n")
        symbol_match = re.search(r"Symbol: ([\w:]+)", text)
        lots_match = re.search(r"LOTS: ([\d,]+)", text)
        future_price_match = re.search(r"FUTURE PRICE: ([\d.]+)", text)
        type_match = re.search(r"🚨 (.*?)\s", text)
        time_match = re.search(r"TIME: ([\d:]+)", text)
        
        if symbol_match and lots_match:
            symbol = symbol_match.group(1).replace("NFO:", "").replace("MCX:", "")
            
            # Smart Base Symbol Detection
            base_symbol = "UNKNOWN"
            for asset in ASSETS:
                if symbol.startswith(asset):
                    base_symbol = asset
                    break
            
            strike = 0
            opt_type = "FUT"
            strike_match = re.search(r"(\d+)(CE|PE)", symbol)
            if strike_match:
                strike = int(strike_match.group(1))
                opt_type = strike_match.group(2)
            
            action = type_match.group(1) if type_match else "UNKNOWN"
            lots = int(lots_match.group(1).replace(",", ""))
            
            # Action Category Logic
            category = "Neutral"
            if "BUY" in action: category = "LONG BUILDUP"
            elif "SHORT COVERING" in action: category = "SHORT COVERING"
            elif "WRITER" in action or "SELL" in action: category = "SHORT BUILDUP"
            elif "LONG UNWINDING" in action: category = "LONG UNWINDING"

            # Net Sentiment Score
            score = 0
            if category in ["LONG BUILDUP", "SHORT COVERING"]:
                score = lots if (opt_type == "CE" or opt_type == "FUT") else -lots
            elif category in ["SHORT BUILDUP", "LONG UNWINDING"]:
                score = -lots if (opt_type == "CE" or opt_type == "FUT") else lots

            messages.append({
                "BaseSymbol": base_symbol,
                "Symbol": symbol,
                "Strike": strike,
                "Type": opt_type,
                "Action": action,
                "Category": category,
                "Lots": lots,
                "FuturePrice": float(future_price_match.group(1)) if future_price_match else 0,
                "Score": score,
                "Time": time_match.group(1) if time_match else "00:00:00"
            })
    return pd.DataFrame(messages)

# --- APP LAYOUT ---
st.title("🏛️ Institutional Dashboard (Live Hybrid)")

if os.path.exists(LIVE_DATA_FILE):
    with open(LIVE_DATA_FILE, "r") as f:
        live_data = json.load(f)
    st.subheader("⚡ Live Market Feed (Zerodha API)")
    z_cols = st.columns(len(live_data))
    for i, (symbol, data) in enumerate(live_data.items()):
        clean_sym = symbol.replace("NFO:", "").replace("NSE:", "").replace("MCX:", "")
        z_cols[i].metric(clean_sym, f"{data['last_price']:,.2f}", delta=f"OI: {data['oi']:,.0f}")
    st.markdown("---")

if os.path.exists(DATA_FILE):
    df = parse_html_data(DATA_FILE)
    selected_base = st.sidebar.selectbox("🎯 Target Asset", ASSETS)
    f_df = df[df['BaseSymbol'] == selected_base].copy()

    if not f_df.empty:
        pe_total = f_df[f_df['Type'] == 'PE']['Lots'].sum()
        ce_total = f_df[f_df['Type'] == 'CE']['Lots'].sum()
        pcr = pe_total / ce_total if ce_total > 0 else 1.0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("PCR (Net Volume)", f"{pcr:.2f}")
        
        sentiment = "Neutral"
        if pcr > 1.2: sentiment = "🚀 EXTREME BULLISH"
        elif pcr > 1.0: sentiment = "🟢 BULLISH"
        elif pcr < 0.8: sentiment = "🔴 BEARISH"
        elif pcr < 0.6: sentiment = "💀 EXTREME BEARISH"
        col2.subheader(f"Sentiment: {sentiment}")

        latest_px = f_df['FuturePrice'].iloc[-1]
        col3.metric("LTP (Telegram)", f"{latest_px:,.2f}")

        st.markdown("---")
        st.subheader("📊 Intraday Build-up Tracker")
        b_cols = st.columns(4)
        for i, cat in enumerate(["LONG BUILDUP", "SHORT COVERING", "SHORT BUILDUP", "LONG UNWINDING"]):
            count = f_df[f_df['Category'] == cat]['Lots'].sum()
            b_cols[i].metric(cat, f"{count:,.0f} Lots")

        st.markdown("---")
        st.subheader("🧱 Institutional Walls (S/R)")
        # S/R Walls Calculation
        opt_data = f_df[f_df['Strike'] > 0]
        if not opt_data.empty:
            ce_data = opt_data[opt_data['Type'] == 'CE']
            pe_data = opt_data[opt_data['Type'] == 'PE']
            
            res_wall = ce_data.groupby('Strike')['Lots'].sum().idxmax() if not ce_data.empty else "N/A"
            sup_wall = pe_data.groupby('Strike')['Lots'].sum().idxmax() if not pe_data.empty else "N/A"
            
            w1, w2 = st.columns(2)
            w1.error(f"Strongest Resistance (Max CE): {res_wall}")
            w2.success(f"Strongest Support (Max PE): {sup_wall}")
        else:
            st.info("No option data available for walls.")

        st.subheader("💡 Logic Recommendation")
        if pcr > 1.1:
            st.success("**BUY ON DIPS:** PCR indicates buyers are dominating.")
        elif pcr < 0.9:
            st.error("**SELL ON RISES:** Smart money is writing calls.")
        else:
            st.warning("**WAIT FOR BREAKOUT:** No clear trend.")

        st.subheader("⛓️ Live Option Chain Heatmap")
        # Dynamic Step Logic for MCX and Nifty
        if "NIFTY" in selected_base or "CRUDEOIL" == selected_base:
            step = 100
        else:
            step = 10
            
        atm = round(latest_px / step) * step
        strikes = [atm + (i * step) for i in range(-5, 6)]
        oc_list = []
        for s in strikes:
            s_data = f_df[f_df['Strike'] == s]
            ce_lots = s_data[s_data['Type'] == 'CE']['Lots'].sum()
            pe_lots = s_data[s_data['Type'] == 'PE']['Lots'].sum()
            oc_list.append({"Strike": s, "CE Lots (Resistance)": ce_lots, "PE Lots (Support)": pe_lots, "Bias": pe_lots - ce_lots})
        st.table(pd.DataFrame(oc_list))
else:
    st.error("Please upload raw_data.html to start analysis.")
