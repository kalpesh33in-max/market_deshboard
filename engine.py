import os
import json
import pandas as pd
from kiteconnect import KiteConnect, KiteTicker

API_KEY = os.environ.get("API_KEY")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Load instruments
df = pd.read_csv("instruments.csv")

# Filter symbols
TARGETS = ["BANKNIFTY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK"]

tokens = []

for sym in TARGETS:
    temp = df[df['name'] == sym]
    tokens += temp['instrument_token'].tolist()

live_data = {}

def on_ticks(ws, ticks):
    global live_data

    for t in ticks:
        token = t['instrument_token']
        live_data[token] = {
            "ltp": t.get("last_price", 0),
            "oi": t.get("oi", 0),
            "volume": t.get("volume", 0)
        }

    with open("live_data.json", "w") as f:
        json.dump(live_data, f)


def on_connect(ws, response):
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_FULL, tokens)


kws = KiteTicker(API_KEY, ACCESS_TOKEN)
kws.on_ticks = on_ticks
kws.on_connect = on_connect

kws.connect(threaded=False)
