
import time
import os
import json
import pyotp
import pandas as pd
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION (Local File) ---
INSTRUMENTS_FILE = "instruments.csv"

API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
USER_ID = os.environ.get("USER_ID")
PASSWORD = os.environ.get("PASSWORD")
TOTP_SECRET = os.environ.get("TOTP_SECRET")

LIVE_DATA_FILE = "live_data.json"
ASSETS = ["BANKNIFTY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "CRUDEOIL", "CRUDEOILM"]

def get_automated_token():
    kite = KiteConnect(api_key=API_KEY)
    login_url = kite.login_url()
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    try:
        driver.get(login_url)
        time.sleep(3)
        driver.find_element(By.XPATH, "//input[@type='text']").send_keys(USER_ID)
        driver.find_element(By.XPATH, "//input[@type='password']").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(3)
        totp = pyotp.TOTP(TOTP_SECRET)
        token = totp.now()
        driver.find_element(By.XPATH, "//input[@type='number']").send_keys(token)
        time.sleep(10)
        current_url = driver.current_url
        if "request_token=" in current_url:
            request_token = current_url.split("request_token=")[1].split("&")[0]
            data = kite.generate_session(request_token, api_secret=API_SECRET)
            return data["access_token"]
        return None
    except Exception as e:
        print(f"Login Failed: {e}")
        return None
    finally:
        driver.quit()

def get_watchlist_from_csv():
    if not os.path.exists(INSTRUMENTS_FILE):
        print(f"Error: {INSTRUMENTS_FILE} not found in the dashboard folder.")
        return ["NSE:NIFTY BANK"]
        
    print(f"Loading instruments from local {INSTRUMENTS_FILE}...")
    df = pd.read_csv(INSTRUMENTS_FILE)
    watchlist = ["NSE:NIFTY BANK"]
    
    for asset in ASSETS:
        futs = df[(df['name'] == asset) & (df['segment'].str.contains('FUT'))].copy()
        if not futs.empty:
            futs['expiry'] = pd.to_datetime(futs['expiry'])
            nearest = futs.sort_values(by='expiry').iloc[0]
            symbol = f"{nearest['exchange']}:{nearest['tradingsymbol']}"
            watchlist.append(symbol)
            print(f"Watchlist Added: {symbol}")
    return watchlist

def run_bridge():
    if not all([API_KEY, API_SECRET, USER_ID, PASSWORD, TOTP_SECRET]):
        print("Error: Missing Environment Variables.")
        return

    access_token = get_automated_token()
    if not access_token: return

    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(access_token)
    
    watchlist = get_watchlist_from_csv()
    print("✅ Zerodha Live Bridge (Local CSV Mode) Started.")
    
    while True:
        try:
            quotes = kite.quote(watchlist)
            live_data = {s: {"last_price": d['last_price'], "oi": d['oi'], "volume": d['volume'], "timestamp": str(d['timestamp'])} for s, d in quotes.items()}
            with open(LIVE_DATA_FILE, "w") as f: json.dump(live_data, f)
            time.sleep(5)
        except Exception as e:
            print(f"Bridge Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bridge()
