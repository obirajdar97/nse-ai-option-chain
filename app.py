import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrapper
import yfinance as yf

st.set_page_config(page_title="AI Option Chain & Swing Trading Desk", layout="wide")

# --- MATHEMATICAL CALCULATIONS ENGINE (OPTIONS) ---
def compute_max_pain(rows_df):
    min_pain = float('inf')
    mp = 0
    unique_strikes = rows_df['strike'].unique()
    for s in unique_strikes:
        pain = 0
        for _, row in rows_df.iterrows():
            pain += row['ce_oi'] * max(s - row['strike'], 0)
            pain += row['pe_oi'] * max(row['strike'] - s, 0)
        if pain < min_pain:
            min_pain = pain
            mp = s
    return mp

# --- DATA FULFILLMENT: LIVE INTRADAY OPTION CHAIN ---
def fetch_option_chain_data(symbol):
    try:
        payload = nse_optionchain_scrapper(symbol)
        if not payload or 'records' not in payload:
            return None
            
        records = payload.get('records', {})
        spot = records.get('underlyingValue', 0)
        expiries = records.get('expiryDates', [])
        nearest_expiry = expiries[0] if expiries else ''
        
        rows = []
        for item in records.get('data', []):
            if item.get('expiryDate') != nearest_expiry:
                continue
            strike = item.get('strikePrice', 0)
            ce = item.get('CE', {})
            pe = item.get('PE', {})
            
            rows.append({
                'strike': float(strike),
                'ce_oi': float(ce.get('openInterest', 0) if ce else 0),
                'ce_ltp': float(ce.get('lastPrice', 0) if ce else 0),
                'pe_oi': float(pe.get('openInterest', 0) if pe else 0),
                'pe_ltp': float(pe.get('lastPrice', 0) if pe else 0)
            })
            
        if len(rows) == 0:
            return None
            
        df = pd.DataFrame(rows).sort_values('strike')
        step = 50 if symbol == 'NIFTY' else 100
        atm = round(spot / step) * step
        
        total_ce_oi = df['ce_oi'].sum()
        total_pe_oi = df['pe_oi'].sum()
        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
        pcr_label = 'BULLISH' if pcr > 1.15 else 'BEARISH' if pcr < 0.85 else 'NEUTRAL'
        
        max_pain = compute_max_pain(df)
        
        top_ce = df[df['strike'] > spot].nlargest(1, 'ce_oi')
        top_pe = df[df['strike'] < spot].nlargest(1, 'pe_oi')
        resistance = int(top_ce['strike'].iloc[0]) if len(top_ce) > 0 else atm + step
        support = int(top_pe['strike'].iloc[0]) if len(top_pe) > 0 else atm - step
        
        return {
            "spot": spot, "atm": atm, "expiry": nearest_expiry, "max_pain": max_pain,
            "pcr": pcr, "pcr_label": pcr_label, "resistance": resistance, "support": support, "df": df
        }
    except Exception as e:
        return None

# --- DATA FULFILLMENT: REAL STOCKS DATA FOR SWING TRADING ---
def fetch_swing_stock_data(stock_ticker):
    try:
        # Appends .NS automatically for National Stock Exchange tickers
        ticker = f"{stock_ticker}.NS"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y") # Fetch past 1 year to analyze trends securely
        
        if hist.empty:
            return None
            
        latest_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        daily_pct_change = ((latest_close - prev_close) / prev_close) * 100
        
        # Calculate key technical pillars for swing trades
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # Simple volume spike tracker
        avg_volume = hist['Volume'].tail(20).mean()
        latest_volume = hist['Volume'].iloc[-1]
        volume_spike = latest_volume / avg_volume
        
        return {
            "close": latest_close,
            "change": daily_pct_change,
            "ma50": ma_50,
            "ma200": ma_200,
            "volume_mult": volume_spike,
            "raw_hist": hist.tail(10) # Send last 10 days table data
        }
    except Exception as e:
        st.error(f"Error fetching stock rows: {e}")
        return None

# --- MAIN SURFACE APPLICATION LAYOUT ---
st.title("📈 Advanced AI Options & Swing Trading Hub")

# USER TRAINING PLAYBOOK EXPANDER
with st.expander("ℹ️ Click here for the Updated User Guide"):
    st.markdown("""
    ### 🧭 How to Navigate the Modes:
    1. **Live Intraday Tracking Mode:** Select this during market hours (9:15 AM - 3:30 PM). It analyzes the Index Option Chain (PCR, Max Pain) to find fast momentum.
    2. **After-Market Setup / Swing Trading Mode:** Select this after hours or over weekends. It switches to **Actual Stocks / Shares**. It analyzes support levels using moving averages and volume breakouts to pick trades you can hold for days or weeks.
    """)

# APP SYSTEM CONTROLS
st.markdown("### ⚙️ Workspace Configuration Control")
app_mode = st.radio("Choose Your Active Trading Field Context:", ["Live Intraday Tracking", "After-Market Setup / Swing Trading"], horizontal=True)

st.markdown("---")

# --- MODE 1: LIVE INTRADAY OPTION CHAIN ---
if app_mode == "Live Intraday Tracking":
    asset = st.selectbox("Select Derivative Index Index", ["NIFTY", "BANKNIFTY"])
    
    if st.button("🔄 Execute Live Option Analysis"):
        with st.spinner("Streaming real-time option blocks..."):
            metrics = fetch_option_chain_data(asset)
            
            if metrics:
                # Dashboard Cards
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Underlying Spot Price", f"₹ {metrics['spot']:.2f}")
                m2.metric("ATM Center Strike", f"{metrics['atm']:,}")
                m3.metric("Option Chain PCR", f"{metrics['pcr']}", f"Bias: {metrics['pcr_label']}")
                m4.metric("Computed Max Pain", f"{metrics['max_pain']:,}")
                
                # AI Signaling Room
                st.subheader("🎯 Automated AI Intraday Trading Signal")
                if metrics['pcr'] > 1.15:
                    st.success("🚀 **AI Signal: STRONG BULLISH INTRADAY MOMENTUM**")
                    st.info(f"**Strategy:** Buy ATM Call Option near {metrics['atm']} or deploy a Bull Call Spread. \n\n**Target:** ₹ {metrics['resistance']} | **Stop Loss:** ₹ {metrics['atm'] - 50 if asset == 'NIFTY' else metrics['atm'] - 150}")
                elif metrics['pcr'] < 0.85:
                    st.error("📉 **AI Signal: STRONG BEARISH INTRADAY PRESSURE**")
                    st.info(f"**Strategy:** Buy ATM Put Option near {metrics['atm']} or deploy a Bear Put Spread. \n\n**Target:** ₹ {metrics['support']} | **Stop Loss:** ₹ {metrics['atm'] + 50 if asset == 'NIFTY' else metrics['atm'] + 150}")
                else:
                    st.warning("🔄 **AI Signal: RANGEBOUND / NEUTRAL MARKET**")
                    st.info(f"**Strategy:** Sell option premiums out-of-the-money or deploy an Iron Condor. \n\n**Target Target:** Expect settlement decay approaching the Max Pain point at {metrics['max_pain']}.")
                
                # Table Data View
                st.subheader("📋 Sliced Options Matrix View")
                grid = metrics['df'].copy()
                strikes = sorted(grid['strike'].tolist())
                atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - metrics['spot']))
                final_grid = grid[grid['strike'].isin(strikes[max(0, atm_idx-5):min(len(strikes), atm_idx+6)])].copy()
                final_grid.columns = ['Strike Price', 'CE Open Interest', 'CE LTP (₹)', 'PE Open Interest', 'PE LTP (₹)']
                st.dataframe(final_grid[['CE Open Interest', 'CE LTP (₹)', 'Strike Price', 'PE LTP (₹)', 'PE Open Interest']], use_container_width=True)
            else:
                st.error("NSE Live servers are currently offline or busy. If the market is closed, please switch to 'After-Market Setup / Swing Trading' above.")

# --- MODE 2: AFTER-MARKET / SWING TRADING INDIVIDUAL STOCKS ---
else:
    st.markdown("### 🦅 Swing Stock Analysis Panel")
    stock_choice = st.selectbox("Select Blue-Chip Stock to Evaluate for Next-Day / Swing Setup:", ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN"])
    
    if st.button("🔍 Scan Stock for Swing Trade Structure"):
        with st.spinner(f"Extracting server delivery data profiles for {stock_choice}..."):
            s_data = fetch_swing_stock_data(stock_choice)
            
            if s_data:
                # Dashboard Cards
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Closing Share Price", f"₹ {s_data['close']:.2f}", f"{s_data['change']:.2f}% Change")
                s2.metric("50-Day Moving Avg (Short Trend)", f"₹ {s_data['ma50']:.2f}")
                s3.metric("200-Day Moving Avg (Long Trend)", f"₹ {s_data['ma200']:.2f}")
                s4.metric("Volume Multiplier vs Average", f"{s_data['volume_mult']:.2f}x")
                
                st.markdown("---")
                
                # AI Swing Advice Logic System
                st.subheader("🤖 AI Algorithmic Swing Trading Recommendation")
                
                # Rule 1: Buying pullbacks in a strong long term uptrend
                if s_data['close'] > s_data['ma200'] and s_data['close'] <= (s_data['ma50'] * 1.02) and s_data['close'] >= (s_data['ma50'] * 0.98):
                    st.success("🟢 **AI SWING SETUP: HIGH PROBABILITY BUY ON PULLBACK**")
                    st.write(f"**Action Plan:** Enter swing long position near current price of ₹{s_data['close']:.2f}. The stock is resting right on its 50-Day Moving Average Support within a macro uptrend.")
                    st.write(f"🎯 **Target:** ₹ {s_data['close'] * 1.06:.2f} (6% Upside Move) | 🛑 **Stop Loss:** ₹ {s_data['ma50'] * 0.96:.2f} (Closing Basis)")
                    
                # Rule 2: Volume breakout entry
                elif s_data['close'] > s_data['ma50'] and s_data['volume_mult'] > 1.5:
                    st.success("🚀 **AI SWING SETUP: VOLUME BREAKOUT VALIDATED**")
                    st.write(f"**Action Plan:** Momentum swing entry. The stock closing today showed an institutional volume spike of `{s_data['volume_mult']:.2f}x` regular averages. High chance of continuation tomorrow.")
                    st.write(f"🎯 **Target:** ₹ {s_data['close'] * 1.08:.2f} (8% Breakout Run) | 🛑 **Stop Loss:** ₹ {s_data['close'] * 0.95:.2f}")
                    
                # Rule 3: No clear setup / wait
                else:
                    st.warning("🟡 **AI SWING SETUP: NEUTRAL COOLDOWN ZONE (WATCHLIST ONLY)**")
                    st.write("**Action Plan:** Do not enter a trade immediately. The share price is floating between core trend levels without an explicit volume breakout trigger. Keep on watchlist and wait for a pullback closer to major moving average baselines.")
                
                # Display Historical Data Grid 
                st.markdown("---")
                st.subheader("📊 Recent 10-Day Closing Prices Historical Log")
                raw_grid = s_data['raw_hist'].copy()
                raw_grid.index = raw_grid.index.strftime('%Y-%m-%d')
                st.dataframe(raw_grid[['Open', 'High', 'Low', 'Close', 'Volume']], use_container_width=True)
            else:
                st.error("Failed to collect historical price matrix. Please verify internet connection protocols.")
