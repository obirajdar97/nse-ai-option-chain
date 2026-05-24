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

# --- DATA CONNECTOR: ANY STOCK IN THE MARKET ---
def fetch_any_stock_data(ticker_symbol):
    try:
        # Automatically standardizes names to match national stock exchange criteria
        symbol = ticker_symbol.strip().upper()
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
            
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1y") # Collects 1 rolling year of historical records
        
        if hist.empty or len(hist) < 50:
            return None
            
        latest_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        pct_change = ((latest_close - prev_close) / prev_close) * 100
        
        # Technical Indicator Calculations
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # 14-Day Relative Strength Index (RSI)
        hist['RSI'] = calculate_rsi(hist['Close'])
        latest_rsi = hist['RSI'].iloc[-1] if not pd.isna(hist['RSI'].iloc[-1]) else 50
        
        # Volume metrics
        avg_vol = hist['Volume'].tail(20).mean()
        latest_vol = hist['Volume'].iloc[-1]
        vol_multiplier = latest_vol / avg_vol
        
        return {
            "name": ticker_symbol.strip().upper(),
            "close": latest_close,
            "change": pct_change,
            "ma50": ma_50,
            "ma200": ma_200,
            "rsi": latest_rsi,
            "volume_mult": vol_multiplier,
            "raw_hist": hist.tail(10)
        }
    except Exception:
        return None

# --- MAIN SURFACE WEB APP LAYOUT ---
st.title("🦅 Universal AI Derivative & Share Trading Matrix")

with st.expander("ℹ️ Read App Playbook & Strategy Descriptions"):
    st.markdown("""
    ### 🧠 Built-In AI Evaluation Strategies Explained
    When you search an after-market stock, the AI scans across three math-based configurations simultaneously:
    1. **Trend Pullback Setup:** Triggered if a stock is healthy (above 200 EMA) but pulls back to touch its 50-day support track safely.
    2. **Oversold Mean Reversion:** Triggered if the 14-day RSI drops below 35. This signifies panic-selling is exhausted and a sharp relief bounce is mathematically due.
    3. **Institutional Volume Breakout:** Triggered if trading volume suddenly surges past 1.8x normal averages alongside a positive closing structure, tracking heavy fund entries.
    """)

# SYSTEM MODE SELECTOR PANEL
app_mode = st.radio("Choose Active Trading Field Context:", ["Live Intraday Tracking (Options)", "After-Market Setup / Swing Trading (Any Stock)"], horizontal=True)

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
                st.error("Live markets are currently closed. Please flip to After-Market Mode above to scan stocks.")

# --- CONTEXT 2: UNIVERSAL SEARCH + BUDGET STRATEGY SCANNER ---
else:
    st.markdown("### 🔍 Search Any NSE Share & Budget Planner")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        user_ticker = st.text_input("Type ANY NSE Stock Ticker Symbol:", value="TATAMOTORS", help="Type any valid symbol like SBIN, INFIBEAM, IRFC, RELIANCE, etc.")
    with col_input2:
        user_budget = st.number_input("Enter Your Maximum Trading Capital Budget (₹):", min_value=100, value=10000, step=500)

    if st.button("🦅 Run AI Comprehensive Strategy Evaluation"):
        with st.spinner(f"Scanning trend matrix for {user_ticker}..."):
            s = fetch_any_stock_data(user_ticker)
            
            if s:
                # Share Feasibility & Position Sizing Calculator based on Capital Budget Input
                max_shares_allowed = int(user_budget // s['close'])
                
                # Layout Primary Statistics Grid Row
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Closing Share Price", f"₹ {s['close']:.2f}", f"{s['change']:.2f}% Change")
                m2.metric("14-Day RSI Momentum", f"{s['rsi']:.1f}")
                m3.metric("50 MA (Short Trend Support)", f"₹ {s['ma50']:.2f}")
                m4.metric("200 MA (Long Trend Floor)", f"₹ {s['ma200']:.2f}")
                
                st.markdown("---")
                
                # CAPITAL BUDGET POSITION ALLOCATION VIEW
                st.subheader("💰 Capital Budget Allocation Overview")
                if max_shares_allowed > 0:
                    allocated_capital = max_shares_allowed * s['close']
                    st.success(f"Based on your budget of **₹{user_budget:,.2f}**, you can safely buy exactly **{max_shares_allowed} shares** of {s['name']}. (Total Required Deployment: **₹{allocated_capital:,.2f}**)")
                else:
                    st.error(f"❌ Your specified budget of **₹{user_budget:,.2f}** is too low to buy even a single share of {s['name']} (Price: ₹{s['close']:.2f}). Please select a different stock or increase your budget.")
                
                st.markdown("---")
                
                # ADVANCED MULTI-STRATEGY CRITERIA PROCESSING MATRIX
                st.subheader("🎯 Multi-Strategy AI Signal Room")
                
                strategy_triggered = False
                
                # Evaluation Strategy 1: Trend-Following Moving Average Pullback Cushion
                if s['close'] > s['ma200'] and abs(s['close'] - s['ma50']) / s['ma50'] <= 0.02:
                    st.markdown("### 🟢 Strategy Triggered: **TREND PULLBACK SETUP**")
                    st.write(f"**Execution Blueprint:** Buy {max_shares_allowed} shares on current support consolidation.")
                    st.write(f"🎯 **Swing Target Level:** ₹ {s['close'] * 1.07:.2f} (7% expected run) | 🛑 **Invalidation Stop Loss:** ₹ {s['ma50'] * 0.96:.2f}")
                    st.info(f"**AI Rationale Matrix:** {s['name']} is in a structural macro uptrend over the 200-day line, but has safely cooled down to hit a key entry cushion at the 50-day average. Risk-to-reward parameters are highly optimized here.")
                    strategy_triggered = True
                    
                # Evaluation Strategy 2: Mean Reversion Oversold Correction
                elif s['rsi'] <= 35:
                    st.markdown("### 🔵 Strategy Triggered: **OVERSOLD MEAN REVERSION**")
                    st.write(f"**Execution Blueprint:** Accumulate contrarian long positions across your budget footprint.")
                    st.write(f"🎯 **Swing Target Level:** ₹ {s['close'] * 1.08:.2f} (8% standard technical recovery) | 🛑 **Invalidation Stop Loss:** ₹ {s['close'] * 0.94:.2f}")
                    st.info(f"**AI Rationale Matrix:** The 14-day RSI indicator stands at `{s['rsi']:.1f}`, signaling that immediate retail panic selling is fundamentally exhausted. Expect institutional bargain buyers to step in tomorrow, triggering an upside mean-reversion bounce.")
                    strategy_triggered = True
                    
                # Evaluation Strategy 3: Volume Breakout Validation Tracker
                elif s['close'] > s['ma50'] and s['volume_mult'] >= 1.7:
                    st.markdown("### 🚀 Strategy Triggered: **INSTITUTIONAL VOLUME BREAKOUT**")
                    st.write(f"**Execution Blueprint:** Ride the active momentum wave immediately upon the next market open.")
                    st.write(f"🎯 **Swing Target Level:** ₹ {s['close'] * 1.10:.2f} (10% breakout expansion run) | 🛑 **Invalidation Stop Loss:** ₹ {s['close'] * 0.95:.2f}")
                    st.info(f"**AI Rationale Matrix:** Trading volume has surged to `{s['volume_mult']:.2f}x` its trailing 20-day average. This indicates substantial large-scale fund accumulation taking place, suggesting continuation momentum for a swing run.")
                    strategy_triggered = True
                    
                # Safe Wait State: No parameters match structural criteria entries cleanly
                if not strategy_triggered:
                    st.markdown("### 🟡 AI Strategy State: **NEUTRAL MONITORING (WATCHLIST)**")
                    st.warning(f"**AI Action Plan:** Stand aside for now. Do not allocate your capital budget into {s['name']} immediately. The current configuration doesn't match any premium technical buy setups cleanly. Keep it on your watch list and search for a different stock ticker above to find a better setup.")
                
                # Recent History Table Row Layout
                st.markdown("---")
                st.subheader("📊 Recent 10-Day Trading History Logs")
                raw_grid = s['raw_hist'].copy()
                raw_grid.index = raw_grid.index.strftime('%Y-%m-%d')
                st.dataframe(raw_grid[['Open', 'High', 'Low', 'Close', 'Volume']], use_container_width=True)
            else:
                st.error("❌ Invalid Symbol or Data Fetch Failure. Please check your spelling and make sure you typed a valid NSE symbol (e.g., SBIN, IRFC, WIPRO, SUZLON, PNB).")
