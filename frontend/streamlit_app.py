import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import time
from datetime import datetime, timezone
from contextlib import contextmanager

import os
import sys

# Ensure the root 'financial_ai' folder is in sys.path so 'backend' can be resolved via absolute import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- BOOTSTRAP: Package Discovery ---
try:
    from backend.app.services.stock_service import stock_service
    from backend.app.services.news_service import news_service
    from backend.app.ai.analyst import analyst_agent
    from backend.app.schemas.stock import StockDataResponse
    from backend.app.services import portfolio_service
    from backend.app.services.mpt_service import optimize_portfolio
    from backend.app.core.database import SessionLocal
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
    page_title="FinAI Crystal Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── DYNAMIC CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Syne:wght@400;500;600;700;800&display=swap');

:root {
    --bg-primary:   #080C14;
    --bg-secondary: #0D1320;
    --bg-card:      #0F1928;
    --bg-hover:     #162235;
    --accent-gold:  #F0B90B;
    --accent-teal:  #00D4AA;
    --accent-red:   #FF4444;
    --accent-blue:  #1E88E5;
    --text-primary: #E8EDF5;
    --text-muted:   #6B7A99;
    --border:       #1A2740;
}

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 2rem 2rem 2rem; }

.terminal-header {
    background: linear-gradient(135deg, #080C14 0%, #0D1928 50%, #080C14 100%);
    border-bottom: 2px solid var(--border);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -2rem 1.5rem -2rem;
}
.terminal-logo { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 800; color: var(--text-primary); }
.terminal-logo span { color: var(--accent-gold); text-shadow: 0 0 12px var(--accent-gold); }

.status-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 800;
    background: rgba(0, 212, 170, 0.1);
    color: var(--accent-teal);
    border: 1px solid var(--accent-teal);
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem;
    position: relative;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.metric-card:hover { border-color: var(--accent-gold); transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
.metric-label { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 2px; }
.metric-value { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; margin: 0.2rem 0; }

/* Pulse Animation */
.pulse { animation: pulse-red 2s infinite; }
@keyframes pulse-red {
    0% { opacity: 1; }
    50% { opacity: 0.4; }
    100% { opacity: 1; }
}

.news-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 0.8rem;
    border-left: 5px solid var(--accent-blue);
    transition: transform 0.2s;
}
.news-card:hover { transform: scale(1.02); background: var(--bg-hover); }

/* Tabs */
div[data-baseweb="tab-list"] { background-color: var(--bg-secondary) !important; padding: 5px; border-radius: 10px; }
button[data-baseweb="tab"] { color: var(--text-muted) !important; font-size: 0.8rem; font-weight: bold; }
button[aria-selected="true"] { color: var(--accent-gold) !important; background: transparent !important; }

/* Custom Chat Style */
.stChatMessage { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: 12px !important; }

</style>
""", unsafe_allow_html=True)

# ─── STATE MANAGEMENT ────────────────────────────────────────────────────────
if "ticker" not in st.session_state: st.session_state.ticker = "RELIANCE.NS"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "agent_logs" not in st.session_state: st.session_state.agent_logs = ["● SYSTEM READY"]

def add_log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    st.session_state.agent_logs.append(f"● {ts} | {msg}")
    if len(st.session_state.agent_logs) > 8: st.session_state.agent_logs.pop(0)

def trigger_scan(new_ticker):
    st.session_state.ticker = new_ticker.upper()
    add_log(f"INIT SCAN: {new_ticker}")

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="terminal-header">
    <div class="terminal-logo">CRYSTAL<span>ALPHA</span> TERMINAL 6.0</div>
    <div style="display:flex; gap:20px; align-items:center;">
        <div class="status-tag">LIVE MARKET STREAMING</div>
        <div style="font-size:0.75rem; color:var(--text-muted)">{datetime.now().strftime('%d %b %Y | %H:%M:%S')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 ASSET EXPLORER")
    srch = st.text_input("Enter Symbol (NSE/BSE/US)", value=st.session_state.ticker, label_visibility="collapsed")
    if st.button("EXECUTE ANALYSIS ⚡", use_container_width=True):
        trigger_scan(srch)
    
    st.markdown("---")
    st.markdown("### 💼 QUICK TRADE")
    col_q1, col_q2 = st.columns(2)
    qty = col_q1.number_input("QTY", min_value=1, value=10)
    if col_q2.button("BUY POS", type="primary", use_container_width=True):
        with get_db_session() as db:
            ports = portfolio_service.get_all_portfolios(db)
            if not ports:
                p = portfolio_service.create_portfolio(db, "Main Terminal Port")
            else:
                p = ports[0]
            # Fetch current price for trade
            p_data = stock_service.get_current_price(st.session_state.ticker)
            portfolio_service.record_transaction(db, p.id, st.session_state.ticker, "BUY", qty, p_data['price'])
            add_log(f"TRADE EXECUTED: Bought {qty} {st.session_state.ticker}")
            st.toast("Trade Confirmed & Logged!")

    st.markdown("---")
    st.markdown("### 📡 AGENT CONSOLE")
    for log in reversed(st.session_state.agent_logs):
        st.caption(log)

# ─── DATA LAYER ───
@st.cache_data(ttl=60)
def fetch_full_intel(symbol):
    sd_dict = stock_service.get_full_stock_data(symbol)
    hist_dict = stock_service.get_historical_data(symbol, period="3mo")
    news_dict = news_service.get_news_for_symbol(symbol, limit=10)
    return sd_dict, hist_dict, news_dict

try:
    with st.spinner("QUANT REASONING IN PROGRESS..."):
        sd_data, h_data, n_data = fetch_full_intel(st.session_state.ticker)
        sd = StockDataResponse(**sd_data)
        hist = pd.DataFrame(h_data['data'])

    # ── TOP METRICS PULSE ──
    c1, c2, c3, c4 = st.columns(4)
    chg = ((sd.current_price - sd.previous_close) / sd.previous_close * 100) if sd.previous_close else 0.0
    chg_color = "var(--accent-teal)" if chg >= 0 else "var(--accent-red)"
    
    c1.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">LAST PRICE</div>
        <div class="metric-value" style="color:{chg_color}">₹{sd.current_price:,.2f}</div>
        <div style="font-size:0.75rem; font-weight:700; color:{chg_color}">{chg:+.2f}%</div>
    </div>""", unsafe_allow_html=True)

    m_cap = getattr(sd, 'market_cap', 0)
    c2.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">MARKET CAP</div>
        <div class="metric-value">₹{m_cap/1e12:,.2f}T</div>
        <div style="font-size:0.75rem; color:var(--text-muted)">Exchange: {sd.exchange}</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">RSI MOMENTUM</div>
        <div class="metric-value" style="color:var(--accent-gold)">{sd.rsi:.1f}</div>
        <div style="font-size:0.75rem; color:var(--text-muted)">{"OVERBOUGHT" if sd.rsi > 70 else "OVERSOLD" if sd.rsi < 30 else "NEUTRAL"}</div>
    </div>""", unsafe_allow_html=True)

    pe = getattr(sd, 'pe_ratio', 0)
    c4.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">P/E RATIO (TTM)</div>
        <div class="metric-value" style="color:var(--accent-blue)">{pe if pe else 'N/A'}</div>
        <div style="font-size:0.75rem; color:var(--text-muted)">Yield: {100/pe if pe and pe > 0 else 0:.2f}%</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ── TABS ──
    tabs = st.tabs(["📉 CHARTS & INDICATORS", "🤖 AI RESEARCH AGENT", "💼 PORTFOLIO ANALYTICS", "📰 MARKET INTELLIGENCE"])

    # 1. Charts
    with tabs[0]:
        col_c, col_g = st.columns([3, 1])
        with col_c:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
            fig.add_trace(go.Candlestick(x=hist['date'], open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Bar(x=hist['date'], y=hist['volume'], name='Volume', marker_color='rgba(30,136,229,0.3)'), row=2, col=1)
            fig.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(13,19,32,0.5)', showlegend=False, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        with col_g:
            st.markdown("#### MOMENTUM GAUGE")
            fig_rsi = go.Figure(go.Indicator(
                mode = "gauge+number", value = sd.rsi,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': "#F0B90B"},
                    'steps': [{'range': [0, 30], 'color': "#FF4444"}, {'range': [70, 100], 'color': "#00D4AA"}],
                }
            ))
            fig_rsi.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_rsi, use_container_width=True)

    # 2. AI Agent
    with tabs[1]:
        st.markdown("### 🤖 SYNERGY NODE REASONING")
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        
        if chat_p := st.chat_input("Ask: 'Does this stock have upside bias?'"):
            st.session_state.chat_history.append({"role": "user", "content": chat_p})
            with st.chat_message("user"): st.markdown(chat_p)
            with st.chat_message("assistant"):
                with st.status("Agent Orchestrating Pipelines...", expanded=True) as status:
                    st.write("🔍 Loading Technical Signals...")
                    add_log("[AGENT] Node: TechScan")
                    time.sleep(0.5)
                    st.write("📰 Reading News Sentiment...")
                    add_log("[AGENT] Node: Sentiment")
                    time.sleep(0.5)
                    st.write("🧠 Synthesizing Final Verdict...")
                    add_log("[AGENT] Node: FinalSynthesis")
                    
                    analysis = analyst_agent.analyze_stock(sd, n_data)
                    ans = f"**VERDICT: {analysis.verdict} ({analysis.confidence}%)**\n\n{analysis.reasoning_summary}\n\n**RISK ASSESSMENT:** {analysis.risk_assessment}"
                    status.update(label="Synthesis Complete!", state="complete")
                
                st.markdown(ans)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})

    # 3. Portfolio
    with tabs[2]:
        st.markdown("### 📊 QUANTITATIVE PORTFOLIO MATRIX")
        with get_db_session() as db:
            ports = portfolio_service.get_all_portfolios(db)
            if not ports:
                st.warning("NO PORTFOLIO DETECTED. CLICK 'BUY POS' IN SIDEBAR TO START.")
            else:
                p_id = ports[0].id
                summary = portfolio_service.get_portfolio_summary(db, p_id)
                t_col1, t_col2 = st.columns([1, 2])
                with t_col1:
                    st.metric("TOTAL INVESTED", f"₹{summary['total_invested']:,.2f}")
                    st.metric("POSITIONS", f"{summary['total_holdings']}")
                    if st.button("RUN MPT OPTIMIZER ⚡", use_container_width=True):
                        tickers = [h['symbol'] for h in summary['holdings']]
                        if len(tickers) < 2:
                            st.error("Need at least 2 tickers for MPT.")
                        else:
                            add_log("[MPT] Solver active")
                            opt = optimize_portfolio(tickers)
                            st.write(opt)
                with t_col2:
                    # EF Visualization
                    if len(summary['holdings']) > 0:
                        df_h = pd.DataFrame(summary['holdings'])
                        fig_p = go.Figure(data=[go.Pie(labels=df_h['symbol'], values=df_h['total_invested'], hole=.4)])
                        fig_p.update_layout(title="Asset Allocation", paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
                        st.plotly_chart(fig_p, use_container_width=True)

    # 4. News
    with tabs[3]:
        st.markdown("### 📡 REAL-TIME INTELLIGENCE FEED")
        articles = n_data.articles if hasattr(n_data, 'articles') else []
        if not articles:
            st.info("No news articles found for this symbol.")
        for art in articles:
            title      = art.title if hasattr(art, 'title') else str(art.get('title', ''))
            source     = art.source if hasattr(art, 'source') else str(art.get('source', 'Unknown'))
            pub_at     = art.published_at if hasattr(art, 'published_at') else art.get('published_at', '')
            summary    = art.summary if hasattr(art, 'summary') else str(art.get('summary', ''))
            st.markdown(f"""
            <div class="news-card">
                <div style="font-size:0.9rem; font-weight:700; color:var(--text-primary)">{title}</div>
                <div style="font-size:0.7rem; color:var(--text-muted); margin: 5px 0;">{source} | {pub_at}</div>
                <div style="font-size:0.8rem; color:var(--text-muted)">{str(summary)[:150]}...</div>
            </div>""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"TERMINAL FAULT: {e}")
    st.info("Ensure backend API and .env are configured.")

# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div style='text-align:center; font-size:0.6rem; color:var(--text-muted)'>TRACK-B ADVANCED · CRYSTAL TERMINAL © 2026</div>", unsafe_allow_html=True)
