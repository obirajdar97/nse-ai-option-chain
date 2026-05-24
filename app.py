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

# --- DATA FULFILLMENT MATRIX ---
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
                'ce_oi': float(ce.get('openInterest', 0)),
                'ce_ltp': float(ce.get('lastPrice', 0)),
                'pe_oi': float(pe.get('openInterest', 0)),
                'pe_ltp': float(pe.get('lastPrice', 0))
            })
            
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
        resistance = int(top_ce['strike'].iloc[0]) if len(top_ce) > 0 else 0
        support = int(top_pe['strike'].iloc[0]) if len(top_pe) > 0 else 0
        
        return {
            "spot": spot, "atm": atm, "expiry": nearest_expiry, "max_pain": max_pain,
            "pcr": pcr, "pcr_label": pcr_label, "resistance": resistance, "support": support, "df": df
        }
    except Exception as e:
        st.error(f"Data Connection Timeout: {e}")
        return None

# --- AI SIGNALS SYSTEM GENERATOR ---
def generate_ai_trade_recommendation(m, operational_mode):
    reco = {}
    if operational_mode == "Live Intraday Tracking":
        # Rapid momentum rules
        if m['pcr'] > 1.15:
            reco['signal'] = "🚀 STRONG BUY (BULLISH)"
            reco['strategy'] = f"Bull Call Spread or Long ATM Call near {m['atm']}"
            reco['target'] = f"{m['resistance']}"
            reco['stop'] = f"{m['atm'] - 50 if asset == 'NIFTY' else m['atm'] - 150}"
            reco['rationale'] = f"PCR is heavily high at {m['pcr']}, meaning put options writers are strongly protecting the baseline floor at {m['support']}. Expect an immediate short-covering rally up toward {m['resistance']}."
        elif m['pcr'] < 0.85:
            reco['signal'] = "📉 STRONG SHORT (BEARISH)"
            reco['strategy'] = f"Bear Put Spread or Long ATM Put near {m['atm']}"
            reco['target'] = f"{m['support']}"
            reco['stop'] = f"{m['atm'] + 50 if asset == 'NIFTY' else m['atm'] + 150}"
            reco['rationale'] = f"PCR indicates weak support at {m['pcr']}. Heavy call writing concentrations sitting at {m['resistance']} are acting as a roof capping any upward spikes."
        else:
            reco['signal'] = "🔄 RANGEBOUND (NEUTRAL MEAN-REVERSION)"
            reco['strategy'] = f"Short Straddle or Iron Condor centered at ATM {m['atm']}"
            reco['target'] = f"{m['max_pain']}"
            reco['stop'] = "Exit if boundaries are crossed aggressively on volume."
            reco['rationale'] = f"The index is tightly balanced with a stable PCR of {m['pcr']}. Options premiums are melting down cleanly toward the Max Pain magnet at {m['max_pain']}."
    else:
        # Swing trade setups / after-market models
        if m['pcr'] > 1.0:
            reco['signal'] = "📈 SWING LONG POSITION"
            reco['strategy'] = f"Sell Put Options below {m['support']} or execute a Bullish Position for next expiry."
            reco['target'] = f"{m['resistance'] + 100}"
            reco['stop'] = f"Daily close below {m['support']}"
            reco['rationale'] = "Option structures carry a long-biased structural holding premium. Safe position configurations look clean right below the major support cluster."
        else:
            reco['signal'] = "📉 SWING SHORT POSITION"
            reco['strategy'] = f"Sell Call Options above {m['resistance']} or deploy a Bearish Position for next expiry."
            reco['target'] = f"{m['support'] - 100}"
            reco['stop'] = f"Daily close above {m['resistance']}"
            reco['rationale'] = "After-hours distribution models display overhead supply clusters. High-probability premium decay resides behind the call resistance wall."
            
    return reco

# --- MAIN SURFACE APPLICATION LAYOUT ---
st.title("📊 Professional AI Derivative Analytics Platform")

# FEATURE 1: ENHANCED INTERACTIVE USER GUIDE
with st.expander("ℹ️ Click here for the Enhanced Interactive App User Guide"):
    st.markdown("""
    ### 🧭 Quick Training Playbook
    Welcome to your personal AI trading workspace. Here is how to navigate and interpret the data frames step-by-step:
    
    1. **Asset Selection:** Use the dropdown menu below to select **NIFTY** or **BANKNIFTY**.
    2. **Operational Framework Mode:** * Select **Live Intraday Tracking** during active trading hours (9:15 AM - 3:30 PM IST) for immediate price actions.
       * Select **After-Market Setup / Swing Trading** after 3:30 PM IST or over weekends to compute overnight support matrices for the next session.
    3. **The Core Financial Indicators:**
       * **Spot Price:** The current actual trading value of the index.
       * **Put-Call Ratio (PCR):** Above 1.15 is Bullish; Below 0.85 is Bearish. It shows where big institutions are putting their money.
       * **Max Pain:** The mathematical anchor point where option writers make the most profit. Prices tend to gravitale here near expiry.
    4. **AI Trade Signal Room:** The automated engine evaluates the option chain structure and provides targeted trade layouts complete with Targets, Stops, and clear rationales.
    """)

# SCREEN SELECTION SETTINGS CONTROLS
st.markdown("### ⚙️ Workspace Workspace Control Controls")
c_col1, c_col2 = st.columns(2)
with c_col1:
    asset = st.selectbox("Select Target Trading Index", ["NIFTY", "BANKNIFTY"])
with c_col2:
    # FEATURE 2: TWO DISTINCT FIELDS FOR LIVE vs AFTER-MARKET
    app_mode = st.radio("Choose Operational Context Field:", ["Live Intraday Tracking", "After-Market Setup / Swing Trading"])

st.markdown("---")

if st.button("🔄 Execute Option Chain Analysis Stream"):
    with st.spinner("Processing official exchange transaction logs..."):
        metrics = fetch_option_chain_data(asset)
        
        if metrics:
            # Row 1 Display Metrics Overview
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Underlying Spot Price", f"₹ {metrics['spot']:.2f}")
            m2.metric("ATM Center Strike", f"{metrics['atm']:,}")
            m3.metric("Option Chain PCR", f"{metrics['pcr']}", f"Bias: {metrics['pcr_label']}")
            m4.metric("Computed Max Pain", f"{metrics['max_pain']:,}")
            
            st.markdown("---")
            
            # FEATURE 3: AI TARGETED TRADE ADVICE SECTION
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
            
            # Row 4 Clean Sliced Option Chain UI Grid Table
            st.subheader(f"📋 Option Chain Slices around ATM (Nearest Expiry: {metrics['expiry']})")
            grid = metrics['df'].copy()
            strikes = sorted(grid['strike'].tolist())
            atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - metrics['spot']))
            
            final_grid = grid[grid['strike'].isin(strikes[max(0, atm_idx-6):min(len(strikes), atm_idx+7)])].copy()
            final_grid.columns = ['Strike Price', 'CE Open Interest', 'CE LTP (₹)', 'PE Open Interest', 'PE LTP (₹)']
            final_grid = final_grid[['CE Open Interest', 'CE LTP (₹)', 'Strike Price', 'PE LTP (₹)', 'PE Open Interest']]
            
            st.dataframe(final_grid.style.highlight_max(axis=0, subset=['CE Open Interest', 'PE Open Interest'], color='#f0fdf4'), use_container_width=True)
        else:
            st.error("No raw data could be processed. If the market is closed and public data access is limited, make sure you are using the 'After-Market Setup' selection filter.")
