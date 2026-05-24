import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrapper
import json

st.set_page_config(page_title="Free AI Option Chain Workspace", layout="wide")

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
        # Fetching directly from free public scrapers
        payload = nse_optionchain_scrapper(symbol)
        
        if not payload or 'records' not in payload:
            st.error("No response from exchange servers. Try refreshing during market hours.")
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
        pcr_label = 'BULLISH' if pcr > 1.2 else 'BEARISH' if pcr < 0.8 else 'NEUTRAL'
        
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
        st.error(f"Error fetching data: {e}")
        return None

# --- AI INSIGHT SIMULATOR PANEL ---
def ask_ai_agent(metrics, query=None):
    if query:
        return f"🤖 **AI Strategy Assistant:** Analyzing your question on '{query}'—The call resistance barrier at `{metrics['resistance']}` is heavy, and current momentum matches a `{metrics['pcr_label']}` bias."
    else:
        return (
            f"### 🤖 AI Market Structure Summary\n"
            f"- **Trend Profile:** The Put-Call Ratio (PCR) is at `{metrics['pcr']}`, indicating a **{metrics['pcr_label']}** intraday sentiment environment.\n"
            f"- **Key Ranges:** Major technical floor support is holding near `{metrics['support']}`, while sellers have capped upside resistance at `{metrics['resistance']}`.\n"
            f"- **Settlement Anchor:** Max Pain sits firmly at `{metrics['max_pain']}`."
        )

# --- VISUAL STRIP LAYOUT ---
st.title("📈 Free Public AI Option Chain Dashboard")
st.subheader("Zero-broker automated data workspace running fully in the cloud")

asset = st.selectbox("Select Trading Index", ["NIFTY", "BANKNIFTY"])

if st.button("Fetch & Analyze Live Data"):
    with st.spinner("Streaming real-time option logs..."):
        metrics = fetch_option_chain_data(asset)
        
        if metrics:
            # Row 1 Display Matrix Cards
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Spot Price", f"₹ {metrics['spot']:.2f}")
            col2.metric("ATM Strike", f"{metrics['atm']:,}")
            col3.metric("PCR Ratio", f"{metrics['pcr']}", f"Stance: {metrics['pcr_label']}")
            col4.metric("Max Pain", f"{metrics['max_pain']:,}")
            
            st.markdown("---")
            
            # Row 2 AI Agent Segment
            st.subheader("🤖 Options Analyst Assistant Workspace")
            ai_side, user_side = st.columns([3, 2])
            with ai_side:
                st.markdown(ask_ai_agent(metrics))
            with user_side:
                st.write("💬 **Consult Assistant**")
                u_msg = st.text_input("Ask about hedge adjustments or entry views:", placeholder="Is current call wall strong?")
                if u_msg:
                    st.info(ask_ai_agent(metrics, u_msg))
                    
            st.markdown("---")
            
            # Row 3 Option Chain Submatrix Table Grid
            st.subheader(f"📊 Option Chain Slices (Expiry: {metrics['expiry']})")
            grid = metrics['df'].copy()
            strikes = sorted(grid['strike'].tolist())
            atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - metrics['spot']))
            
            # Show 6 strikes above and below ATM
            final_grid = grid[grid['strike'].isin(strikes[max(0, atm_idx-6):min(len(strikes), atm_idx+7)])]
            final_grid.columns = ['Strike Price', 'CE Open Interest', 'CE LTP (₹)', 'PE Open Interest', 'PE LTP (₹)']
            final_grid = final_grid[['CE Open Interest', 'CE LTP (₹)', 'Strike Price', 'PE LTP (₹)', 'PE Open Interest']]
            
            st.dataframe(final_grid.style.highlight_max(axis=0, subset=['CE Open Interest', 'PE Open Interest'], color='#f0fdf4'), use_container_width=True)
