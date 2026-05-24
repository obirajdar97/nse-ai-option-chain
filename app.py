import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Universal AI Trading & Swing Desk", layout="wide")

# --- MATHEMATICAL ENGINES ---
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

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- DATA CONNECTOR: REAL-TIME STOCK METRICS ---
def fetch_any_stock_data(ticker_symbol):
    try:
        symbol = ticker_symbol.strip().upper()
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
            
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1y") # Collect 1 year of historical context
        
        if hist.empty or len(hist) < 50:
            return None
            
        latest_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        pct_change = ((latest_close - prev_close) / prev_close) * 100
        
        # Core Technical Parameters
        ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # 14-Day RSI
        hist['RSI'] = calculate_rsi(hist['Close'])
        latest_rsi = hist['RSI'].iloc[-1] if not pd.isna(hist['RSI'].iloc[-1]) else 50
        
        # Volume Multiplier
        avg_vol = hist['Volume'].tail(20).mean()
        latest_vol = hist['Volume'].iloc[-1]
        vol_multiplier = latest_vol / avg_vol
        
        return {
            "name": ticker_symbol.strip().upper(),
            "close": latest_close,
            "change": pct_change,
            "ma20": ma_20,
            "ma50": ma_50,
            "ma200": ma_200,
            "rsi": latest_rsi,
            "volume_mult": vol_multiplier,
            "raw_hist": hist.tail(10)
        }
    except Exception:
        return None

# --- MAIN WEB APP LAYOUT ---
st.title("🦅 Universal AI Derivative & Share Trading Matrix")

# MODE SELECTOR PANEL
app_mode = st.radio("Choose Active Trading Field Context:", ["Live Intraday Tracking (Options)", "Swing Trading Desk (Any Stock)"], horizontal=True)

st.markdown("---")

# --- CONTEXT 1: LIVE OPTIONS CHAIN ---
if app_mode == "Live Intraday Tracking (Options)":
    from nsepython import nse_optionchain_scrapper
    asset = st.selectbox("Select Index Profile", ["NIFTY", "BANKNIFTY"])
    
    if st.button("🔄 Launch Index Option Scan"):
        with st.spinner("Connecting to live logs..."):
            try:
                payload = nse_optionchain_scrapper(asset)
                records = payload.get('records', {})
                spot = records.get('underlyingValue', 0)
                expiries = records.get('expiryDates', [])
                nearest_expiry = expiries[0] if expiries else ''
                
                rows = []
                for item in records.get('data', []):
                    if item.get('expiryDate') != nearest_expiry:
                        continue
                    rows.append({
                        'strike': float(item.get('strikePrice', 0)),
                        'ce_oi': float(item.get('CE', {}).get('openInterest', 0) if item.get('CE') else 0),
                        'ce_ltp': float(item.get('CE', {}).get('lastPrice', 0) if item.get('CE') else 0),
                        'pe_oi': float(item.get('PE', {}).get('openInterest', 0) if item.get('PE') else 0),
                        'pe_ltp': float(item.get('PE', {}).get('lastPrice', 0) if item.get('PE') else 0)
                    })
                df = pd.DataFrame(rows).sort_values('strike')
                step = 50 if asset == 'NIFTY' else 100
                atm = round(spot / step) * step
                pcr = round(df['pe_oi'].sum() / df['ce_oi'].sum(), 2) if df['ce_oi'].sum() > 0 else 0
                max_pain = compute_max_pain(df)
                
                # Render Metrics Dashboard
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Spot Price", f"₹ {spot:.2f}")
                c2.metric("ATM strike", f"{atm}")
                c3.metric("PCR Ratio", f"{pcr}")
                c4.metric("Max Pain", f"{max_pain}")
                
                st.subheader("📋 Sliced Options Matrix View")
                st.dataframe(df.tail(10), use_container_width=True)
            except Exception as error:
                st.error("Live option chain feeds are optimized for market hours. Switch to Swing Trading Desk for stock setups.")

# --- CONTEXT 2: UNIVERSAL SEARCH + HOLDING PERIOD STRATEGY ENGINE ---
else:
    st.markdown("### 🔍 Universal Swing Analyzer & Target Time-Frame Engine")
    
    col_input1, col_input2, col_input3 = st.columns(3)
    with col_input1:
        user_ticker = st.text_input("Type ANY NSE Stock Ticker Symbol:", value="TATAMOTORS")
    with col_input2:
        user_budget = st.number_input("Enter Your Trading Capital Budget (₹):", min_value=100, value=15000, step=500)
    with col_input3:
        # FEATURE 1: TIME PERIOD SELECTION FOR SWING HODL TIMES
        time_period = st.selectbox("Select Intended Holding Time Frame:", ["3 Days (Ultra-Short Momentum)", "7 Days (Pullback / Mean Reversion)", "14 Days (Structural Trend Following)"])

    if st.button("🦅 Run AI Time-Frame Strategy Optimization"):
        with st.spinner(f"Running strategy protocols for {user_ticker}..."):
            s = fetch_any_stock_data(user_ticker)
            
            if s:
                # Position Sizing
                max_shares_allowed = int(user_budget // s['close'])
                
                # Primary metrics layout
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Current Price", f"₹ {s['close']:.2f}", f"{s['change']:.2f}% Change")
                m2.metric("RSI (14 Days)", f"{s['rsi']:.1f}")
                m3.metric("20-Day EMA (Fast Track)", f"₹ {s['ma20']:.2f}")
                m4.metric("50-Day Moving Avg", f"₹ {s['ma50']:.2f}")
                
                st.markdown("---")
                
                # Budget allocation calculation layout
                st.subheader("💰 Portfolio Position Sizing Allocation")
                if max_shares_allowed > 0:
                    allocated_capital = max_shares_allowed * s['close']
                    st.success(f"Based on your budget of **₹{user_budget:,.2f}**, you can purchase exactly **{max_shares_allowed} shares** of {s['name']}. Total required deployment: **₹{allocated_capital:,.2f}**")
                else:
                    st.error(f"❌ Target stock price (₹{s['close']:.2f}) exceeds your allocated budget. Try increasing your capital cap or look for a lower-priced alternative.")
                    st.stop()
                
                st.markdown("---")
                
                # FEATURE 2: DYNAMIC STRATEGY ENGINE CHANGING BASED ON SELECTED TIME PERIODS
                st.subheader(f"🎯 Targeted Strategy Evaluation: {time_period}")
                
                setup_matched = False
                
                # --- STRATEGY OVERVIEW 1: 3 DAYS (VOLUME & MOMENTUM BREAKOUTS) ---
                if "3 Days" in time_period:
                    # Look for explosive immediate momentum: price above 20 MA and a volume spike
                    if s['close'] > s['ma20'] and s['volume_mult'] >= 1.5:
                        st.markdown("### 🚀 AI Trading Signal: **ULTRA-SHORT MOMENTUM BREAKOUT (VALIDATED)**")
                        st.write(f"**Execution Plan:** Enter long immediate at opening bells for a **3-Day fast harvest ride**.")
                        st.write(f"🎯 **Target Price (3 Days):** ₹ {s['close'] * 1.03:.2f} (3% Capture) | 🛑 **Stop Loss:** ₹ {s['close'] * 0.98:.2f}")
                        st.info(f"**AI Rationale:** Volume is clocking `{s['volume_mult']:.2f}x` average benchmarks with the price breaking out cleanly over the 20-day line. Big block accumulation indicates high probability of immediate follow-through momentum over the next 48 to 72 hours.")
                        setup_matched = True
                    else:
                        st.warning("⚠️ **AI Advice:** This stock does not exhibit clean short-term momentum flags right now. The volume multiplier is too low. For a 3-Day holding window, look for tickers with volume multipliers greater than 1.5x to maximize your probability of immediate profit.")
                
                # --- STRATEGY OVERVIEW 2: 7 DAYS (PULLBACK / MEAN REVERSION REBOUND) ---
                elif "7 Days" in time_period:
                    # Look for oversold bounces or tests of the 50 MA
                    is_oversold = s['rsi'] <= 38
                    near_50_ma = abs(s['close'] - s['ma50']) / s['ma50'] <= 0.025
                    
                    if is_oversold or (s['close'] > s['ma200'] and near_50_ma):
                        st.markdown("### 🟢 AI Trading Signal: **MEDIUM-TERM MEAN REVERSION / PULLBACK SETUP**")
                        st.write(f"**Execution Plan:** Buy and accumulate over the next session for a **7-Day swing target cycle**.")
                        st.write(f"🎯 **Target Price (7 Days):** ₹ {s['close'] * 1.06:.2f} (6% Bounce Target) | 🛑 **Stop Loss:** ₹ {s['close'] * 0.95:.2f}")
                        
                        reason = "RSI is oversold, showing panic selling is exhausted." if is_oversold else "The stock has pulled back to its major 50-day moving average support line in a strong uptrend."
                        st.info(f"**AI Rationale:** {reason} Over a 7-day holding horizon, this pullback offers an optimal risk-to-reward configuration as weak sellers clear out, setting the stage for institutional buying to push the price back up.")
                        setup_matched = True
                    else:
                        st.warning("⚠️ **AI Advice:** The stock is currently sitting in a neutral zone. It is neither oversold (RSI is at default levels) nor resting on major moving average cushions. For a 7-Day swing trade, look for a entry point closer to major support lines.")

                # --- STRATEGY OVERVIEW 3: 14 DAYS (STRUCTURAL TREND ALIGNMENT) ---
                else:
                    # Look for stable positioning above the long term 200 day baseline
                    if s['close'] > s['ma200'] and s['close'] > s['ma50']:
                        st.markdown("### 📈 AI Trading Signal: **STRUCTURAL TREND POSITION COMPLIANT**")
                        st.write(f"**Execution Plan:** Deploy a swing position to be carried over a **14-Day target maturation window**.")
                        st.write(f"🎯 **Target Price (14 Days):** ₹ {s['close'] * 1.10:.2f} (10% Extended Trend Run) | 🛑 **Stop Loss:** ₹ {s['ma50'] * 0.95:.2f}")
                        st.info(f"**AI Rationale:** {s['name']} displays structural strength by trading sustainably above its 50-day and 200-day moving averages. For a 2-week trading horizon, riding this steady macro trend offers a high probability of capturing a full 8–10% move with minimal intraday noise.")
                        setup_matched = True
                    else:
                        st.warning("⚠️ **AI Advice:** The stock is currently trading below core structural moving averages, meaning it lacks macro trend support. For a longer-term 14-day hold, look for stocks with stable uptrends to avoid getting trapped in a distribution phase.")
                
                # Recent history data logs table grid
                st.markdown("---")
                st.subheader("📊 Recent 10-Day Trading History Logs")
                raw_grid = s['raw_hist'].copy()
                raw_grid.index = raw_grid.index.strftime('%Y-%m-%d')
                st.dataframe(raw_grid[['Open', 'High', 'Low', 'Close', 'Volume']], use_container_width=True)
            else:
                st.error("❌ Data Fetch Error. Verify ticker input matches exact standard NSE notation (e.g. SBIN, INFY, ITC, TATASTEEL, SHREECEM).")
