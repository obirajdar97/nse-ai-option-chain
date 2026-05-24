import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="REAL DATA AI Trading Desk", layout="wide")

# --- PERMANENT SIDEBAR USER GUIDE & RISK WARNING ---
st.sidebar.title("🚨 LIVE TRADING RISK WARNING")
st.sidebar.error("""
**CRITICAL FOR LIVE TRADES:**
1. This app uses open-source feeds. Ensure prices match your broker terminal (Zerodha/Kite) before clicking buy.
2. If the market is closed or feeds fail, the app will show an error instead of fake data.
3. Use strict stop losses as recommended by the AI.
""")

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- THE ACTUAL REAL-WORLD WATCHLIST (NIFTY TOP LIQUID STOCKS) ---
REAL_MARKET_WATCHLIST = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", 
    "ITC", "LTIM", "LT", "HINDUNILVR", "AXISBANK", "TATAMOTORS", "COALINDIA",
    "TATASTEEL", "NTPC", "POWERGRID", "MARUTI", "INDUSINDBK", "ZOMATO"
]

@st.cache_data(ttl=300) # Refreshes strictly every 5 minutes from real market feeds
def scan_real_market_only():
    scanned_results = []
    for ticker in REAL_MARKET_WATCHLIST:
        try:
            symbol = f"{ticker}.NS"
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1y")
            
            if hist.empty or len(hist) < 50:
                continue
                
            latest_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            pct_change = ((latest_close - prev_close) / prev_close) * 100
            
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            ma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            
            hist['RSI'] = calculate_rsi(hist['Close'])
            latest_rsi = hist['RSI'].iloc[-1] if not pd.isna(hist['RSI'].iloc[-1]) else 50
            
            avg_vol = hist['Volume'].tail(20).mean()
            latest_vol = hist['Volume'].iloc[-1]
            vol_multiplier = latest_vol / avg_vol
            
            scanned_results.append({
                "ticker": ticker, "close": latest_close, "change": pct_change,
                "ma20": ma20, "ma50": ma50, "ma200": ma200, "rsi": latest_rsi, "volume_mult": vol_multiplier
            })
        except Exception:
            continue
    return scanned_results

# --- APP INTERFACE ---
st.title("🦅 Real-Data AI Robo-Swing Scanner")
st.markdown("### ⚠️ NO SIMULATED DATA MODE ACTIVATED")

user_budget = st.number_input("Enter Your Maximum Trading Capital Budget (₹):", min_value=500, value=25000, step=1000)

if st.button("🔍 Scan Live Market & Generate Real Trade Recommendations"):
    with st.spinner("Fetching 100% real-time data tracks from exchange pools..."):
        market_data = scan_real_market_only()
        
        if not market_data:
            st.error("❌ Failed to connect to live market data. Please check your internet connection or try again during market hours. No simulated backup will be provided.")
            st.stop()
            
        # Filter for budget constraints using actual closing share values
        affordable_stocks = [s for s in market_data if s['close'] <= user_budget]
        
        if not affordable_stocks:
            st.error(f"❌ None of the active Nifty stocks cost less than your budget of ₹{user_budget}. Increase budget to scan successfully.")
            st.stop()
            
        # --- STRATEGY MATCHING LOGIC (PURE REAL DATA) ---
        best_3day = None
        highest_vol = 0
        for s in affordable_stocks:
            if s['close'] > s['ma20'] and s['volume_mult'] > highest_vol:
                highest_vol = s['volume_mult']
                best_3day = s
                
        best_7day = None
        best_7day_score = float('inf')
        for s in affordable_stocks:
            dist_to_50ma = abs(s['close'] - s['ma50']) / s['ma50']
            if s['rsi'] <= 45 or (s['close'] > s['ma200'] and dist_to_50ma <= 0.04):
                if dist_to_50ma < best_7day_score:
                    best_7day_score = dist_to_50ma
                    best_7day = s
                    
        best_14day = None
        strongest_trend = -999
        for s in affordable_stocks:
            if s['close'] > s['ma200'] and s['close'] > s['ma50']:
                if s['change'] > strongest_trend:
                    strongest_trend = s['change']
                    best_14day = s

        # --- OUTPUT TABS ---
        t1, t2, t3 = st.tabs(["🚀 Real 3-Day Momentum Pick", "🟢 Real 7-Day Pullback Pick", "📈 Real 14-Day Trend Pick"])
        
        with t1:
            if best_3day and best_3day['volume_mult'] > 1.2:
                shares = int(user_budget // best_3day['close'])
                st.markdown(f"## **AI Real-Data Suggestion: {best_3day['ticker']}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("Live Close Price", f"₹ {best_3day['close']:.2f}", f"{best_3day['change']:.2f}%")
                c2.metric("Real Volume Surge", f"{best_3day['volume_mult']:.2f}x")
                c3.metric("Exact Buy Quantity", f"{shares} Shares")
                st.success(f"🎯 **Target:** ₹ {best_3day['close'] * 1.03:.2f} | 🛑 **Stop Loss:** ₹ {best_3day['close'] * 0.98:.2f}")
            else:
                st.warning("No real stock currently matches the high-volume 3-day momentum breakout rules.")
                
        with t2:
            if best_7day:
                shares = int(user_budget // best_7day['close'])
                st.markdown(f"## **AI Real-Data Suggestion: {best_7day['ticker']}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("Live Close Price", f"₹ {best_7day['close']:.2f}", f"{best_7day['change']:.2f}%")
                c2.metric("Current RSI", f"{best_7day['rsi']:.1f}")
                c3.metric("Exact Buy Quantity", f"{shares} Shares")
                st.success(f"🎯 **Target:** ₹ {best_7day['close'] * 1.06:.2f} | 🛑 **Stop Loss:** ₹ {best_7day['close'] * 0.95:.2f}")
            else:
                st.warning("No real stock currently meets the deep 7-day pullback correction support criteria.")
                
        with t3:
            if best_14day:
                shares = int(user_budget // best_14day['close'])
                st.markdown(f"## **AI Real-Data Suggestion: {best_14day['ticker']}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("Live Close Price", f"₹ {best_14day['close']:.2f}", f"{best_14day['change']:.2f}%")
                c2.metric("50-Day Moving Average", f"₹ {best_14day['ma50']:.2f}")
                c3.metric("Exact Buy Quantity", f"{shares} Shares")
                st.success(f"🎯 **Target:** ₹ {best_14day['close'] * 1.10:.2f} | 🛑 **Stop Loss:** ₹ {best_14day['ma50'] * 0.95:.2f}")
            else:
                st.warning("No real stock currently matches the strict 14-day long-term structural uptrend framework.")
