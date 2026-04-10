import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import time
from datetime import datetime
from contextlib import contextmanager

# Add the financial_ai/ directory to sys.path so 'backend' resolves as a top-level package.
financial_ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if financial_ai_root not in sys.path:
    sys.path.insert(0, financial_ai_root)

# --- BOOTSTRAP: Package Discovery ---
try:
    from backend.app.services.stock_service import stock_service
    from backend.app.services.news_service import news_service
    from backend.app.ai.analyst import analyst_agent
    from backend.app.schemas.stock import StockDataResponse
    from backend.app.schemas.analysis import FinancialAnalysisResult
    from backend.app.services import portfolio_service
    from backend.app.services.mpt_service import optimize_portfolio
    from backend.app.core.database import SessionLocal
    from backend.app.services.options_service import get_options_chain, black_scholes_call, black_scholes_put
except ImportError as e:
    st.error(f"STRUCTURAL ERROR: Could not find backend modules. Ensure you are running from the project root. (Error: {e})")
    st.stop()

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinAI Terminal",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── DYNAMIC CSS & NOISE FILTER ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    /* Obsidian Quant Palette */
    --bg-primary:   #030303;
    --bg-secondary: #0A0A0C;
    --bg-card:      #0F0F13;
    --bg-hover:     #17171C;
    --accent-neon:  #B026FF; /* Neon Violet */
    --accent-neon-dim:#B026FF33;
    --accent-silver:#D4D4D8;
    --accent-green: #00E676;
    --accent-red:   #FF1744;
    --text-primary: #F4F4F5;
    --text-muted:   #81818B;
    --border:       #1F1F27;
}

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

/* Global noise overlay */
.noise-overlay {
    position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    pointer-events: none;
    z-index: 9999;
    opacity: 0.05;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem; max-width: 1600px; }

/* Micro-Interaction & Rounded System */
.obsidian-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 2rem; /* 32px smooth radius */
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.obsidian-card::before {
    content: '';
    position: absolute;
    top: 0; left: -100%; width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(176, 38, 255, 0.05), transparent);
    transition: left 0.6s ease;
}
.obsidian-card:hover::before {
    left: 100%;
}
.obsidian-card:hover {
    border-color: rgba(176, 38, 255, 0.4);
    transform: translateY(-2px) scale(1.01);
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7), 0 0 20px rgba(176, 38, 255, 0.1);
}

.terminal-header {
    background: linear-gradient(to bottom, var(--bg-secondary) 0%, transparent 100%);
    border-radius: 2.5rem;
    padding: 1.5rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    border: 1px solid var(--border);
    backdrop-filter: blur(10px);
}
.terminal-logo { 
    font-family: 'Inter', sans-serif; 
    font-size: 1.8rem; 
    font-weight: 800; 
    letter-spacing: -1px;
}
.terminal-logo span { 
    color: var(--accent-neon); 
    text-shadow: 0 0 15px var(--accent-neon-dim); 
}

.status-indicator {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 14px;
    border-radius: 2rem;
    font-size: 0.75rem;
    font-weight: 700;
    background: var(--accent-neon-dim);
    color: var(--accent-neon);
    border: 1px solid rgba(176, 38, 255, 0.3);
}
.status-dot {
    width: 6px; height: 6px;
    background-color: var(--accent-neon);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--accent-neon);
    animation: pulse 2s infinite;
}

.metric-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
.metric-value { font-family: 'Inter', sans-serif; font-size: 2.2rem; font-weight: 700; margin: 0.3rem 0; letter-spacing: -1px; }

@keyframes pulse {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(1.2); }
    100% { opacity: 1; transform: scale(1); }
}

/* Tabs */
div[data-baseweb="tab-list"] { background-color: transparent !important; gap: 10px; border-bottom: 1px solid var(--border); padding-bottom: 0px;}
button[data-baseweb="tab"] { 
    color: var(--text-muted) !important; font-size: 0.85rem; font-weight: 600; 
    border-radius: 1rem 1rem 0 0 !important;
    padding: 10px 20px !important;
    transition: all 0.3s ease;
}
button[aria-selected="true"] { 
    color: var(--accent-neon) !important; 
    background: var(--bg-card) !important; 
    border-bottom: 2px solid var(--accent-neon) !important;
}

/* AI Verdict Styling */
.verdict-box {
    border-radius: 1.5rem;
    padding: 1.5rem;
    margin-bottom: 1rem;
    text-align: center;
    border: 1px solid var(--border);
}
.verdict-BUY { background: rgba(0, 230, 118, 0.05); border-color: var(--accent-green); color: var(--accent-green); }
.verdict-SELL { background: rgba(255, 23, 68, 0.05); border-color: var(--accent-red); color: var(--accent-red); }
.verdict-HOLD { background: rgba(212, 212, 216, 0.05); border-color: var(--accent-silver); color: var(--accent-silver); }

.verdict-title { font-family: 'Inter', sans-serif; font-size: 2rem; font-weight: 800; letter-spacing: 2px; }

/* Custom Chat Style */
.stChatMessage { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: 2rem !important; padding: 1.5rem !important; }

/* System Status Footer */
.footer-system {
    position: fixed; bottom: 0; left: 0; width: 100%;
    background: var(--bg-card);
    border-top: 1px solid var(--border);
    padding: 8px 24px;
    display: flex; justify-content: space-between;
    font-size: 0.65rem; color: var(--text-muted);
    z-index: 100;
}
</style>

<svg class="noise-overlay" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <filter id="noiseFilter">
    <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch"/>
  </filter>
  <rect width="100%" height="100%" filter="url(#noiseFilter)"/>
</svg>
""", unsafe_allow_html=True)

# ─── STATE MANAGEMENT ────────────────────────────────────────────────────────
if "ticker" not in st.session_state: st.session_state.ticker = "RELIANCE.NS"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "agent_logs" not in st.session_state: st.session_state.agent_logs = ["● SYS_INIT"]

def add_log(msg):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    st.session_state.agent_logs.append(f"[{ts}] {msg}")
    if len(st.session_state.agent_logs) > 10: st.session_state.agent_logs.pop(0)

def trigger_scan(new_ticker):
    st.session_state.ticker = new_ticker.upper()
    add_log(f"EXEC CMD: TARGET_LOCK -> {new_ticker}")

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="terminal-header">
    <div class="terminal-logo">FinAI <span>Terminal</span></div>
    <div style="display:flex; gap:24px; align-items:center;">
        <div style="text-align: right; font-family:'Inter', sans-serif;">
            <div style="font-size:0.75rem; color:var(--text-muted); font-weight:600;">ACTIVE TARGET</div>
            <div style="font-size:1.2rem; color:var(--text-primary); font-weight:800; letter-spacing:1px;">{st.session_state.ticker}</div>
        </div>
        <div class="status-indicator">
            <div class="status-dot"></div>
            QUANT CORE ONLINE
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR "CONTROL SPINE" ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='font-family:Inter; font-weight:800; font-size:1.2rem; margin-bottom:1rem; color:var(--text-primary)'>COMMAND CENTER</div>", unsafe_allow_html=True)
    
    srch = st.text_input("SET TARGET ASSET:", value=st.session_state.ticker)
    if st.button("INITIALIZE PROTOCOL ⚡", type="primary", use_container_width=True):
        trigger_scan(srch)
    
    st.markdown("<br><hr style='border-color:var(--border)'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Inter; font-weight:700; font-size:0.9rem; color:var(--text-muted); margin-bottom:10px;'>EXECUTIVE ACTION</div>", unsafe_allow_html=True)
    
    col_q1, col_q2 = st.columns(2)
    qty = col_q1.number_input("UNITS", min_value=1, value=100, step=10)
    if col_q2.button("EXECUTE BUY", use_container_width=True):
        with get_db_session() as db:
            ports = portfolio_service.get_all_portfolios(db)
            p = ports[0] if ports else portfolio_service.create_portfolio(db, "Alpha Fund")
            p_data = stock_service.get_current_price(st.session_state.ticker)
            portfolio_service.record_transaction(db, p.id, st.session_state.ticker, "BUY", qty, p_data['price'])
            add_log(f"TXN RECORDED: BUY {qty} {st.session_state.ticker}")
            st.toast("Txn Committed to Ledger.")

    st.markdown("<br><hr style='border-color:var(--border)'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Inter; font-weight:700; font-size:0.9rem; color:var(--text-muted); margin-bottom:10px;'>TERMINAL LOGS</div>", unsafe_allow_html=True)
    log_html = "<div style='font-family:JetBrains Mono; font-size:0.65rem; color:var(--accent-neon-dim);'>"
    for log in reversed(st.session_state.agent_logs):
        log_html += f"<div style='margin-bottom:4px; opacity:0.8; color:var(--accent-silver)'>{log}</div>"
    log_html += "</div>"
    st.markdown(log_html, unsafe_allow_html=True)

# ─── DATA LAYER ───
@st.cache_data(ttl=60, show_spinner=False)
def fetch_full_intel(symbol):
    sd_dict = stock_service.get_full_stock_data(symbol)
    hist_dict = stock_service.get_historical_data(symbol, period="3mo")
    news_dict = news_service.get_news_for_symbol(symbol, limit=8)
    return sd_dict, hist_dict, news_dict

@st.cache_data(ttl=900, show_spinner=False)
def fetch_ai_analysis(symbol, _sd_obj, _n_data_obj):
    try:
        return analyst_agent.analyze_stock(_sd_obj, _n_data_obj)
    except Exception as e:
        return FinancialAnalysisResult(
            verdict="HOLD", 
            confidence=0, 
            reasoning_summary=f"⚠️ Quantum Node Offline / LLM Timeout: {e}",
            risk_assessment="Assessment unavailable."
        )

@st.cache_data(ttl=300, show_spinner=False)
def fetch_cached_options(symbol):
    try:
        return get_options_chain(symbol)
    except Exception as e:
        return {"status": "error", "message": f"Derivatives chain unavailable: {e}"}

# Load main info
try:
    with st.spinner("QUANT REASONING IN PROGRESS..."):
        sd_data, h_data, n_data = fetch_full_intel(st.session_state.ticker)
        sd = StockDataResponse(**sd_data)
        
        if getattr(sd, 'current_price', 0) == 0.0:
            st.error(f"⚠️ SIGNAL LOST: Symbol '{sd.symbol}' invalid or lacks liquidity.")
            st.stop()
            
        hist = pd.DataFrame(h_data['data'])

    # ── KPI STRIP "LIVE SIGNAL BAND" ──
    c1, c2, c3, c4 = st.columns(4)
    chg = ((sd.current_price - sd.previous_close) / sd.previous_close * 100) if sd.previous_close else 0.0
    chg_color = "var(--accent-green)" if chg >= 0 else "var(--accent-red)"
    chg_sign = "+" if chg >= 0 else ""
    
    c1.markdown(f"""
    <div class="obsidian-card">
        <div class="metric-label">LTP • {sd.exchange}</div>
        <div class="metric-value" style="color:var(--text-primary)">₹{sd.current_price:,.2f}</div>
        <div style="font-size:0.85rem; font-weight:600; color:{chg_color}">{chg_sign}{chg:.2f}%</div>
    </div>""", unsafe_allow_html=True)

    m_cap = getattr(sd, 'market_cap', 0)
    c2.markdown(f"""
    <div class="obsidian-card">
        <div class="metric-label">MARKET CAP</div>
        <div class="metric-value">₹{m_cap/1e12:,.2f}T</div>
        <div style="font-size:0.85rem; color:var(--text-muted)">Free Float Valuation</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="obsidian-card">
        <div class="metric-label">RSI MOMENTUM</div>
        <div class="metric-value" style="color:var(--accent-neon)">{sd.rsi:.1f}</div>
        <div style="font-size:0.85rem; color:var(--text-muted)">{"OVERBOUGHT" if sd.rsi > 70 else "OVERSOLD" if sd.rsi < 30 else "NEUTRAL MOMENTUM"}</div>
    </div>""", unsafe_allow_html=True)

    pe = getattr(sd, 'pe_ratio', 0)
    c4.markdown(f"""
    <div class="obsidian-card">
        <div class="metric-label">P/E RATIO (TTM)</div>
        <div class="metric-value">{pe if pe else 'N/A'}</div>
        <div style="font-size:0.85rem; color:var(--text-muted)">Yield: {100/pe if pe and pe > 0 else 0:.2f}%</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ── TABS CORE UI ──
    tabs = st.tabs([
        "THE DECISION ENGINE", 
        "PORTFOLIO INTELLIGENCE", 
        "COMPARISON PROTOCOL",
        "ADVANCED QUANT LAYER"
    ])

    # 1. Decision Engine (Chart + AI)
    with tabs[0]:
        st.markdown("<br>", unsafe_allow_html=True)
        col_chart, col_ai = st.columns([1.5, 1])
        
        with col_chart:
            st.markdown("<div style='font-family:Inter; font-weight:700; color:var(--accent-silver); margin-bottom:15px;'>MARKET VISUALIZATION PLANE</div>", unsafe_allow_html=True)
            # Create Plotly Chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)
            fig.add_trace(go.Candlestick(
                x=hist['date'], open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], 
                name='Price',
                increasing_line_color='#00E676', decreasing_line_color='#FF1744'
            ), row=1, col=1)
            fig.add_trace(go.Bar(
                x=hist['date'], y=hist['volume'], name='Volume', 
                marker_color='rgba(176,38,255,0.2)', marker_line_color='rgba(176,38,255,0.5)', marker_line_width=1
            ), row=2, col=1)
            
            # Obsidian Chart Styling
            fig.update_layout(
                height=600, 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                showlegend=False, 
                xaxis_rangeslider_visible=False,
                margin=dict(l=0, r=0, t=10, b=0),
                font=dict(family="JetBrains Mono", color="#81818B")
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#1F1F27', zeroline=False)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#1F1F27', zeroline=False)
            
            st.plotly_chart(fig, use_container_width=True)

        with col_ai:
            st.markdown("<div style='font-family:Inter; font-weight:700; color:var(--accent-silver); margin-bottom:15px;'>AI INTELLIGENCE CORE</div>", unsafe_allow_html=True)
            
            with st.spinner("Synthesizing Neural Intel..."):
                analysis = fetch_ai_analysis(sd.symbol, sd, n_data)
                
                v_class = "verdict-" + str(analysis.verdict).upper()
                c_bar_width = int(analysis.confidence)
                
                # Render AI Verdict Block
                st.markdown(f"""
                <div class="obsidian-card verdict-box {v_class}">
                    <div style="font-size:0.8rem; font-weight:700; letter-spacing:1px; margin-bottom:5px;">SYSTEM VERDICT</div>
                    <div class="verdict-title">{analysis.verdict}</div>
                    <div style="font-size:0.85rem; margin-top:10px; opacity:0.8;">CONFIDENCE: {analysis.confidence}%</div>
                    <div style="width:100%; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; margin-top:8px;">
                        <div style="width:{c_bar_width}%; height:100%; background:currentColor; border-radius:2px; box-shadow: 0 0 10px currentColor;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<div class='obsidian-card'>", unsafe_allow_html=True)
                st.markdown("**Structured Reasoning:**")
                st.write(analysis.reasoning_summary)
                st.markdown("---")
                st.markdown("**Risk Assessment:**")
                st.write(analysis.risk_assessment)
                st.markdown("</div>", unsafe_allow_html=True)

    # 2. Portfolio MPT
    with tabs[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        with get_db_session() as db:
            ports = portfolio_service.get_all_portfolios(db)
            if not ports:
                st.info("No active portfolios in database. Execute a BUY command in the control spine to establish ledger.")
            else:
                p_id = ports[0].id
                summary = portfolio_service.get_portfolio_summary(db, p_id)
                
                c_mp1, c_mp2 = st.columns([1, 2])
                with c_mp1:
                    st.markdown("<div class='obsidian-card'>", unsafe_allow_html=True)
                    st.markdown("<div style='font-family:Inter; font-weight:700; color:var(--text-muted); margin-bottom:15px;'>ASSET ALLOCATION</div>", unsafe_allow_html=True)
                    st.write(f"**Total Capital Deployed:** ₹{summary['total_invested']:,.2f}")
                    st.write(f"**Open Positions:** {summary['total_holdings']}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("RUN MPT OPTIMIZATION SURFACE ⚡", use_container_width=True, type="primary"):
                        tickers = [h['symbol'] for h in summary['holdings']]
                        if len(tickers) < 2:
                            st.warning("MPT Engine Error: Requires >= 2 assets.")
                        else:
                            add_log("CMD: SOLVER [MPT] ACTIVE")
                            opt = optimize_portfolio(tickers)
                            st.markdown("<div class='obsidian-card' style='border-color:var(--accent-neon);'>", unsafe_allow_html=True)
                            if opt.get("status") == "error":
                                st.error(f"Solver Failure: {opt.get('message')}")
                            else:
                                st.markdown("<div style='color:var(--accent-neon); font-weight:800; font-size:1.1rem;'>OPTIMAL EFFICIENT FRONTIER</div>", unsafe_allow_html=True)
                                st.metric("Max Sharpe Ratio", f"{opt.get('sharpe_ratio', 0):.2f}")
                                st.metric("Exp Annual Return", f"{opt.get('expected_return', 0)*100:.2f}%")
                                st.metric("Volatility (Risk)", f"{opt.get('volatility', 0)*100:.2f}%")
                                st.write("**Ideal Weights:**")
                                st.json(opt.get('weights', {}))
                            st.markdown("</div>", unsafe_allow_html=True)
                
                with c_mp2:
                    if len(summary['holdings']) > 0:
                        df_h = pd.DataFrame(summary['holdings'])
                        fig_p = go.Figure(data=[go.Pie(
                            labels=df_h['symbol'], values=df_h['total_invested'], 
                            hole=.5, marker=dict(colors=["#B026FF", "#00E676", "#FF1744", "#D4D4D8", "#1E88E5"])
                        )])
                        fig_p.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)', 
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#F4F4F5", family="JetBrains Mono"),
                            margin=dict(l=0, r=0, t=20, b=0)
                        )
                        st.plotly_chart(fig_p, use_container_width=True)

    # 3. Comparison
    with tabs[2]:
        st.markdown("<br>", unsafe_allow_html=True)
        c_col1, c_col2 = st.columns([1, 2])
        with c_col1:
            st.markdown("<div class='obsidian-card'>", unsafe_allow_html=True)
            target_cmp = st.text_input("INPUT SECONDARY ASSET:", "MSFT")
            btn_cmp = st.button("INITIALIZE DUAL MAPPING", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        if btn_cmp:
            with c_col2:
                with st.spinner("Mapping Relative Performance..."):
                    try:
                        c_hist = stock_service.get_historical_data(target_cmp, period="3mo")
                        df_c = pd.DataFrame(c_hist['data'])
                        if not df_c.empty and not hist.empty:
                            fig_cmp = go.Figure()
                            # Normalizing to base 100
                            base_m = hist['close'].iloc[0] if len(hist)>0 else 1
                            base_t = df_c['close'].iloc[0] if len(df_c)>0 else 1
                            
                            fig_cmp.add_trace(go.Scatter(x=hist['date'], y=(hist['close']/base_m)*100, name=sd.symbol, line=dict(color='#00E676', width=2)))
                            fig_cmp.add_trace(go.Scatter(x=df_c['date'], y=(df_c['close']/base_t)*100, name=target_cmp.upper(), line=dict(color='#B026FF', width=2)))
                            
                            fig_cmp.update_layout(
                                title="Relative Alpha Generation (Base = 100)",
                                height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(family="JetBrains Mono", color="#81818B")
                            )
                            fig_cmp.update_xaxes(showgrid=True, gridcolor='#1F1F27')
                            fig_cmp.update_yaxes(showgrid=True, gridcolor='#1F1F27')
                            st.plotly_chart(fig_cmp, use_container_width=True)
                    except Exception as e:
                        st.error(f"Mapping Protocol Failed: {e}")

    # 4. Quant Layer / Options
    with tabs[3]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("COMPUTE OPTIONS SURFACE ⚡", type="primary"):
            with st.spinner("Resolving Black-Scholes dynamics..."):
                opt_data = fetch_cached_options(sd.symbol)
                if opt_data.get("status") == "success":
                    st.markdown("<div class='obsidian-card' style='border-color:var(--accent-neon);'>", unsafe_allow_html=True)
                    st.markdown(f"**Target Expiration:** {opt_data['nearest_expiration']}")
                    st.markdown(f"**Market Sentiment (Vol Bias): <span style='color:var(--accent-neon)'>{opt_data['implied_sentiment'].upper()}</span>**", unsafe_allow_html=True)
                    st.markdown("</div><br>", unsafe_allow_html=True)
                    
                    o1, o2 = st.columns(2)
                    with o1:
                        st.markdown("<div style='font-family:Inter; font-weight:700; color:var(--accent-green); margin-bottom:10px;'>CALL PROTOCOL (TOP VOLUME)</div>", unsafe_allow_html=True)
                        if opt_data['active_calls']:
                            st.dataframe(pd.DataFrame(opt_data['active_calls'])[['strike', 'lastPrice', 'volume', 'impliedVolatility']], use_container_width=True)
                    with o2:
                        st.markdown("<div style='font-family:Inter; font-weight:700; color:var(--accent-red); margin-bottom:10px;'>PUT PROTOCOL (TOP VOLUME)</div>", unsafe_allow_html=True)
                        if opt_data['active_puts']:
                            st.dataframe(pd.DataFrame(opt_data['active_puts'])[['strike', 'lastPrice', 'volume', 'impliedVolatility']], use_container_width=True)
                else:
                    st.warning(opt_data.get("message", "Options derivatives unlisted for asset."))

except Exception as e:
    st.error(f"SYSTEM FAULT CRITICAL: {e}")
    st.info("Check neural linkage and backend data stream.")

# ─── SYSTEM FOOTER ───────────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer-system">
    <div>FINAI TERMINAL // TRACK-B ADVANCED</div>
    <div>SYS_STATE: <span style="color:var(--accent-neon);">OPTIMAL</span> | MEMORY: LOCKED</div>
</div>
""", unsafe_allow_html=True)
