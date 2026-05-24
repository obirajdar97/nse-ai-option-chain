import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrapper
import json

st.set_page_config(page_title="Pro Free AI Option Chain Workspace", layout="wide")

# --- MATHEMATICAL CALCULATIONS ENGINE ---
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

# --- DATA FULFILLMENT MATRIX WITH AFTER-MARKET FALLBACK ---
def fetch_option_chain_data(symbol, operational_mode):
    try:
        payload = nse_optionchain_scrapper(symbol)
        
        # Fallback Check: If NSE sends blank data because the market is closed
        if not payload or 'records' not in payload or len(payload.get('records', {}).get('data', [])) == 0:
            if operational_mode == "After-Market Setup / Swing Trading":
                st.warning("⚠️ NSE Live Option Chain is down for maintenance/weekend closure. Generating a simulated structural model based on standard thresholds for planning.")
                # Creating an off-market structural template so your app doesn't break
                sim_spot = 22000.0 if symbol == "NIFTY" else 47000.0
                step = 50 if symbol == "NIFTY" else 100
                sim_atm = round(sim_spot / step) * step
                
                rows = []
                for i in range(-15, 16):
                    strike_val = sim_atm + (i * step)
                    rows.append({
                        'strike': float(strike_val),
                        'ce_oi': float(50000 - abs(i)*2000 if i >=0 else 20000),
                        'ce_ltp': float(max(10, 150 - i*15)),
                        'pe_oi': float(50000 - abs(i)*2000 if i <=0 else 20000),
                        'pe_ltp': float(max(10, 150 + i*15))
                    })
                df = pd.DataFrame(rows).sort_values('strike')
                return {
                    "spot": sim_spot, "atm": sim_atm, "expiry": "Next Active Expiry", "max_pain": sim_atm,
                    "pcr": 1.0, "pcr_label": "NEUTRAL", "resistance": sim_atm + (2*step), "support": sim_atm - (2*step), "df": df
                }
            else:
                return None
            
        records = payload.get('records', {})
        spot = records.get('underlyingValue', 0)
        expiries = records.get('expiryDates', [])
        
        # If weekend, the first expiry might be expired, check list safety
        nearest_expiry = expiries[0] if expiries else ''
        raw_data = records.get('data', [])
        
        rows = []
        for item in raw_data:
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
        st.error(f"NSE Server API Busy or Empty Profile: {e}")
        return None

# --- AI SIGNALS SYSTEM GENERATOR ---
def generate_ai_trade_recommendation(m, operational_mode):
    reco = {}
    if operational_mode == "Live Intraday Tracking":
        if m['pcr'] > 1.15:
            reco['signal'] = "🚀 STRONG BUY (BULLISH INTRADAY)"
            reco['strategy'] = f"Bull Call Spread or Long ATM Call near {m['atm']}"
            reco['target'] = f"{m['resistance']}"
            reco['stop'] = f"{m['atm'] - 50 if asset == 'NIFTY' else m['atm'] - 150}"
            reco['rationale'] = f"Intraday PCR is high at {m['pcr']}. Options volume suggests heavy accumulation of puts protecting the floor. Rapid upward breakout expected."
        elif m['pcr'] < 0.85:
            reco['signal'] = "📉 STRONG SHORT (BEARISH INTRADAY)"
            reco['strategy'] = f"Bear Put Spread or Long ATM Put near {m['atm']}"
            reco['target'] = f"{m['support']}"
            reco['stop'] = f"{m['atm'] + 50 if asset == 'NIFTY' else m['atm'] + 150}"
            reco['rationale'] = f"Bearish sentiment dominating. Major call writers have built a massive ceiling at {m['resistance']} preventing upside movement."
        else:
            reco['signal'] = "🔄 RANGEBOUND (NEUTRAL INTRADAY)"
            reco['strategy'] = f"Short Straddle or Iron Condor centered at ATM {m['atm']}"
            reco['target'] = f"{m['max_pain']}"
            reco['stop'] = "Exit if indices violate support/resistance boundaries on heavy volume."
            reco['rationale'] = f"Balanced market layout. Options premiums are decaying directly toward the Max Pain center gravity point at {m['max_pain']}."
    else:
        # Swing trade setups / after-market models
        if m['pcr'] > 1.0:
            reco['signal'] = "📈 SWING POSITION: POSITION LONG"
            reco['strategy'] = f"Positional Bullish Spread: Sell Put options below safety cushion {m['support']}"
            reco['target'] = f"{m['resistance'] + 100}"
            reco['stop'] = f"Daily closing price drops below {m['support']}"
            reco['rationale'] = "Multi-day open interest structures show long positions building up. Safe premium collection strategies exist well below the primary support cluster."
        else:
            reco['signal'] = "📉 SWING POSITION: POSITION SHORT"
            reco['strategy'] = f"Positional Bearish Spread: Sell Call options above risk threshold {m['resistance']}"
            reco['target'] = f"{m['support'] - 100}"
            reco['stop'] = f"Daily closing price breaks above {m['resistance']}"
            reco['rationale'] = "After-hours distribution trends indicate resistance overhead. Collecting premium behind the key call walls offers high-probability swing decay."
            
    return reco

# --- MAIN SURFACE APPLICATION LAYOUT ---
st.title("📊 Professional AI Derivative Analytics Platform")

with st.expander("ℹ️ Click here for the Enhanced Interactive App User Guide"):
    st.markdown("""
    ### 🧭 Quick Training Playbook
    1. **Asset Selection:** Use the dropdown menu below to select **NIFTY** or **BANKNIFTY**.
    2. **Operational Framework Mode:** * Select **Live Intraday Tracking** during active trading hours (9:15 AM - 3:30 PM IST) for fast data feeds.
       * Select **After-Market Setup / Swing Trading** after hours or on weekends to look at positional ranges without causing software crashes.
    3. **AI Signal Interpretation:** Use the strategy layouts to construct hedge setups rather than entering raw single options blindly.
    """)

st.markdown("### ⚙️ Workspace Control Controls")
c_col1, c_col2 = st.columns(2)
with c_col1:
    asset = st.selectbox("Select Target Trading Index", ["NIFTY", "BANKNIFTY"])
with c_col2:
    app_mode = st.radio("Choose Operational Context Field:", ["Live Intraday Tracking", "After-Market Setup / Swing Trading"])

st.markdown("---")

if st.button("🔄 Execute Option Chain Analysis Stream"):
    with st.spinner("Processing data matrix configuration..."):
        metrics = fetch_option_chain_data(asset, app_mode)
        
        if metrics:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Underlying Spot Price", f"₹ {metrics['spot']:.2f}")
            m2.metric("ATM Center Strike", f"{metrics['atm']:,}")
            m3.metric("Option Chain PCR", f"{metrics['pcr']}", f"Bias: {metrics['pcr_label']}")
            m4.metric("Computed Max Pain", f"{metrics['max_pain']:,}")
            
            st.markdown("---")
            
            st.subheader("🎯 Automated AI Algorithmic Trade Signal Room")
            ai_data = generate_ai_trade_recommendation(metrics, app_mode)
            
            box_color = "🟢" if "BUY" in ai_data['signal'] or "LONG" in ai_data['signal'] else ("🔴" if "SHORT" in ai_data['signal'] else "🟡")
            
            st.markdown(f"### {box_color} **AI System Signal: {ai_data['signal']}**")
            
            a_col1, a_col2, a_col3 = st.columns(3)
            a_col1.info(f"🛠️ **Recommended Strategy Deployment:**\n\n{ai_data['strategy']}")
            a_col2.success(f"🎯 **Target Level Boundary:**\n\n₹ {ai_data['target']}")
            a_col3.error(f"🛑 **Invalidation Stop Level:**\n\n{ai_data['stop']}")
            
            st.warning(f"📝 **AI Structural Rationale Analysis:**\n\n{ai_data['rationale']}")
            
            st.markdown("---")
            
            st.subheader(f"📋 Option Chain Slices around ATM (Nearest Expiry: {metrics['expiry']})")
            grid = metrics['df'].copy()
            strikes = sorted(grid['strike'].tolist())
            atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - metrics['spot']))
            
            final_grid = grid[grid['strike'].isin(strikes[max(0, atm_idx-6):min(len(strikes), atm_idx+7)])].copy()
            final_grid.columns = ['Strike Price', 'CE Open Interest', 'CE LTP (₹)', 'PE Open Interest', 'PE LTP (₹)']
            final_grid = final_grid[['CE Open Interest', 'CE LTP (₹)', 'Strike Price', 'PE LTP (₹)', 'PE Open Interest']]
            
            st.dataframe(final_grid.style.highlight_max(axis=0, subset=['CE Open Interest', 'PE Open Interest'], color='#f0fdf4'), use_container_width=True)
        else:
            st.error("NSE Live data is currently empty. Please switch the toggle on the right to 'After-Market Setup / Swing Trading' to run off-market analytics smoothly.")
