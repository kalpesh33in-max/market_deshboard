
import os
import json
import time
import re
import pandas as pd
import pyotp
import threading
from kiteconnect import KiteConnect
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import streamlit as st

# --- SHARED CONFIG ---
DATA_FILE = "raw_data.html"
LIVE_DATA_FILE = "live_data.json"
INSTRUMENTS_FILE = "instruments.csv"
ASSETS = ["BANKNIFTY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "CRUDEOIL", "CRUDEOILM"]

# --- ZERODHA BRIDGE LOGIC ---
def get_automated_token():
    try:
        kite = KiteConnect(api_key=os.environ.get("API_KEY"))
        login_url = kite.login_url()
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(login_url)
        time.sleep(3)
        driver.find_element(By.XPATH, "//input[@type='text']").send_keys(os.environ.get("USER_ID"))
        driver.find_element(By.XPATH, "//input[@type='password']").send_keys(os.environ.get("PASSWORD"))
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(3)
        totp = pyotp.TOTP(os.environ.get("TOTP_SECRET"))
        driver.find_element(By.XPATH, "//input[@type='number']").send_keys(totp.now())
        time.sleep(10)
        current_url = driver.current_url
        if "request_token=" in current_url:
            request_token = current_url.split("request_token=")[1].split("&")[0]
            data = kite.generate_session(request_token, api_secret=os.environ.get("API_SECRET"))
            return data["access_token"]
        return None
    except Exception as e:
        print(f"Login Failed: {e}")
        return None
    finally:
        driver.quit()

def run_zerodha_bridge():
    access_token = get_automated_token()
    if not access_token: return
    kite = KiteConnect(api_key=os.environ.get("API_KEY"))
    kite.set_access_token(access_token)
    
    # Get Watchlist from CSV
    if os.path.exists(INSTRUMENTS_FILE):
        df = pd.read_csv(INSTRUMENTS_FILE)
        watchlist = ["NSE:NIFTY BANK"]
        for asset in ASSETS:
            futs = df[(df['name'] == asset) & (df['segment'].str.contains('FUT'))].copy()
            if not futs.empty:
                futs['expiry'] = pd.to_datetime(futs['expiry'])
                nearest = futs.sort_values(by='expiry').iloc[0]
                watchlist.append(f"{nearest['exchange']}:{nearest['tradingsymbol']}")
    else:
        watchlist = ["NSE:NIFTY BANK"]
    
    while True:
        try:
            quotes = kite.quote(watchlist)
            live_data = {s: {"last_price": d['last_price'], "oi": d['oi'], "volume": d['volume']} for s, d in quotes.items()}
            with open(LIVE_DATA_FILE, "w") as f: json.dump(live_data, f)
            time.sleep(5)
        except Exception as e:
            time.sleep(10)

# --- START THE BRIDGE IN A BACKGROUND THREAD ---
if 'bridge_started' not in st.session_state:
    thread = threading.Thread(target=run_zerodha_bridge)
    thread.daemon = True
    thread.start()
    st.session_state['bridge_started'] = True

# --- DASHBOARD UI LOGIC ---
st.set_page_config(page_title="🛡️ Institutional Dashboard", layout="wide")

def parse_html_data(file_path):
    if not os.path.exists(file_path): return pd.DataFrame()
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    messages = []
    for msg in soup.find_all('div', class_='text'):
        text = msg.get_text(separator="\n")
        sym_match = re.search(r"Symbol: ([\w:]+)", text)
        lots_match = re.search(r"LOTS: ([\d,]+)", text)
        f_px_match = re.search(r"FUTURE PRICE: ([\d.]+)", text)
        type_match = re.search(r"🚨 (.*?)\s", text)
        if sym_match and lots_match:
            symbol = sym_match.group(1).replace("NFO:", "").replace("MCX:", "")
            base_symbol = "UNKNOWN"
            for a in ASSETS:
                if symbol.startswith(a): base_symbol = a; break
            s_match = re.search(r"(\d+)(CE|PE)", symbol)
            strike = int(s_match.group(1)) if s_match else 0
            opt_type = s_match.group(2) if s_match else "FUT"
            action = type_match.group(1) if type_match else "UNKNOWN"
            lots = int(lots_match.group(1).replace(",", ""))
            cat = "Neutral"
            if "BUY" in action: cat = "LONG BUILDUP"
            elif "SHORT COVERING" in action: cat = "SHORT COVERING"
            elif "WRITER" in action or "SELL" in action: cat = "SHORT BUILDUP"
            elif "LONG UNWINDING" in action: cat = "LONG UNWINDING"
            score = 0
            if cat in ["LONG BUILDUP", "SHORT COVERING"]:
                score = lots if (opt_type == "CE" or opt_type == "FUT") else -lots
            elif cat in ["SHORT BUILDUP", "LONG UNWINDING"]:
                score = -lots if (opt_type == "CE" or opt_type == "FUT") else lots
            messages.append({"BaseSymbol": base_symbol, "Symbol": symbol, "Strike": strike, "Type": opt_type, "Category": cat, "Lots": lots, "FuturePrice": float(f_px_match.group(1)) if f_px_match else 0, "Score": score})
    return pd.DataFrame(messages)

st.title("🛡️ Institutional Hybrid Dashboard")

# Live Bar
if os.path.exists(LIVE_DATA_FILE):
    with open(LIVE_DATA_FILE, "r") as f: live_data = json.load(f)
    cols = st.columns(len(live_data))
    for i, (sym, d) in enumerate(live_data.items()):
        cols[i].metric(sym.split(":")[-1], f"{d['last_price']:,.2f}", f"OI: {d['oi']:,.0f}")
    st.markdown("---")

# Main Analysis
if os.path.exists(DATA_FILE):
    df = parse_html_data(DATA_FILE)
    selected_base = st.sidebar.selectbox("🎯 Target Asset", ASSETS)
    f_df = df[df['BaseSymbol'] == selected_base].copy()
    if not f_df.empty:
        pe_lots = f_df[f_df['Type'] == 'PE']['Lots'].sum()
        ce_lots = f_df[f_df['Type'] == 'CE']['Lots'].sum()
        pcr = pe_lots / ce_lots if ce_lots > 0 else 1.0
        c1, c2, c3 = st.columns(3)
        c1.metric("PCR", f"{pcr:.2f}")
        sent = "BULLISH" if pcr > 1.0 else "BEARISH"
        c2.subheader(f"Sentiment: {'🟢' if sent=='BULLISH' else '🔴'} {sent}")
        latest_px = f_df['FuturePrice'].iloc[-1]
        c3.metric("LTP (Telegram)", f"{latest_px:,.2f}")
        st.markdown("---")
        st.subheader("📊 Build-up Tracker")
        b_cols = st.columns(4)
        for i, cat in enumerate(["LONG BUILDUP", "SHORT COVERING", "SHORT BUILDUP", "LONG UNWINDING"]):
            b_cols[i].metric(cat, f"{f_df[f_df['Category'] == cat]['Lots'].sum():,.0f}")
        st.markdown("---")
        st.subheader("⛓️ Option Chain Bias")
        step = 100 if "NIFTY" in selected_base or "CRUDEOIL" == selected_base else 10
        atm = round(latest_px / step) * step
        strikes = [atm + (i * step) for i in range(-5, 6)]
        oc_list = [{"Strike": s, "CE Lots": f_df[(f_df['Strike']==s) & (f_df['Type']=='CE')]['Lots'].sum(), "PE Lots": f_df[(f_df['Strike']==s) & (f_df['Type']=='PE')]['Lots'].sum()} for s in strikes]
        st.table(pd.DataFrame(oc_list))
else:
    st.error("Upload raw_data.html to see institutional signals.")
