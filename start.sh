#!/bin/bash
# Start the Zerodha Bridge in the background
python zerodha_bridge.py &

# Start the Streamlit Dashboard in the foreground
streamlit run sentiment_app.py --server.port $PORT --server.address 0.0.0.0
