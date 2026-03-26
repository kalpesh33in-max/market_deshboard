
import subprocess
import os
import sys
import time

def main():
    print("🚀 Starting Hybrid Dashboard Launcher...")
    
    # 1. Start the Zerodha Bridge in the background
    print("📡 Launching Zerodha Bridge...")
    bridge_proc = subprocess.Popen([sys.executable, "zerodha_bridge.py"])
    
    # Give the bridge a moment to initialize
    time.sleep(2)
    
    # 2. Start the Streamlit Dashboard
    print("🖥️ Launching Streamlit Dashboard...")
    port = os.environ.get("PORT", "8501")
    try:
        streamlit_proc = subprocess.run([
            "streamlit", "run", "sentiment_app.py", 
            "--server.port", port, 
            "--server.address", "0.0.0.0",
            "--server.headless", "true"
        ])
    except KeyboardInterrupt:
        print("Stopping processes...")
        bridge_proc.terminate()

if __name__ == "__main__":
    main()
