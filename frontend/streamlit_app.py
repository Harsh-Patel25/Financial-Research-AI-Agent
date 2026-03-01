"""
Interactive Streamlit Dashboard - Premium Edition
Full "Bloomberg Terminal" experience with animated components, caching, and multi-timeframe charts.

To run:
python -m streamlit run frontend/streamlit_app.py
"""

import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components
import time

# Add the root directory AND the backend directory so imports for 'app.x' resolve natively
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.services.stock_service import stock_service
from app.services.news_service import news_service
from app.ai.analyst import analyst_agent
from app.schemas.stock import StockDataResponse

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Intelligence Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── MASTER CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=Roboto+Mono:wght@400;600&display=swap');

/* ── Global Background ── */
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
.stApp {
    background: radial-gradient(ellipse at top left, #0f1729 0%, #060b15 60%);
    background-attachment: fixed;
}

/* ── Animated Background Grid ── */
.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none;
    z-index: 0;
}

/* ── Animations ── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
.animated-card {
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    opacity: 0; /* Star hidden until animation runs */
}

/* ── Header Banner ── */
.header-banner {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.8));
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 20px;
    padding: 32px 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.header-banner::after {
    content: '';
    position: absolute;
    top: -50%; right: -20%;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.header-title {
    font-size: 48px; font-weight: 700; color: #fff;
    letter-spacing: -1px; margin: 0;
    background: linear-gradient(90deg, #fff 0%, #93C5FD 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.header-sub {
    font-size: 15px; color: #64748B; margin-top: 6px; font-family: 'Roboto Mono', monospace;
}

/* ── Market Status Dot ── */
.market-status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 14px; border-radius: 50px;
    background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3);
    font-family: 'Roboto Mono', monospace; font-size: 12px;
    color: #10B981; font-weight: 600; letter-spacing: 1px;
}
.status-dot {
    width: 8px; height: 8px; background: #10B981; border-radius: 50%;
    box-shadow: 0 0 8px #10B981;
    animation: pulse-green 2s infinite;
}
@keyframes pulse-green {
    0%,100% { opacity:1; transform:scale(1); }
    50% { opacity:0.6; transform:scale(1.4); }
}

/* ── Glass Cards ── */
.glass-card {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    transition: all 0.3s ease;
}
.glass-card:hover { border-color: rgba(59,130,246,0.2); box-shadow: 0 0 20px rgba(59,130,246,0.05); }

/* ── Metric Cards (custom) ── */
.mc {
    background: rgba(15,23,42,0.7);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 22px 18px;
    text-align: center;
    margin-bottom: 14px;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.mc:hover { border-color: rgba(59,130,246,0.5); transform: translateY(-4px); box-shadow: 0 8px 24px rgba(59,130,246,0.15); }
.mc-label { font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; margin-bottom: 8px; }
.mc-value { font-size: 36px; font-weight: 700; color: #F1F5F9; line-height: 1; margin-bottom: 6px; font-family: 'Roboto Mono', monospace; text-shadow: 0 0 10px rgba(255,255,255,0.1); }
.mc-sub { font-size: 13px; font-weight: 600; font-family: 'Roboto Mono', monospace; }
.up { color: #10B981; text-shadow: 0 0 8px rgba(16,185,129,0.3); }
.down { color: #EF4444; text-shadow: 0 0 8px rgba(239,68,68,0.3); }
.warn { color: #F59E0B; text-shadow: 0 0 8px rgba(245,158,11,0.3); }
.muted { color: #64748B; }

/* ── Sentiment Badge ── */
.sbadge {
    display: block; text-align: center; padding: 12px 0;
    border-radius: 12px; font-size: 28px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 3px;
    font-family: 'Roboto Mono', monospace;
    text-shadow: 0 0 15px currentColor;
    transition: transform 0.2s;
}
.sbadge:hover { transform: scale(1.02); }
.sbadge.BULLISH  { color:#10B981; background:rgba(16,185,129,0.08); border:2px solid rgba(16,185,129,0.3); }
.sbadge.BEARISH  { color:#EF4444; background:rgba(239,68,68,0.08);  border:2px solid rgba(239,68,68,0.3); }
.sbadge.NEUTRAL  { color:#F59E0B; background:rgba(245,158,11,0.08); border:2px solid rgba(245,158,11,0.3); }

/* ── Trading Signal Row ── */
.signals-row { display:flex; gap:10px; margin: 22px 0 10px; }
.signal-chip {
    flex: 1; text-align: center; padding: 14px;
    border-radius: 12px; font-weight: 700;
    font-size: 13px; text-transform: uppercase; letter-spacing: 1px;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.signal-active-buy { background: rgba(16,185,129,0.15); border: 1.5px solid #10B981; color: #10B981; box-shadow: 0 0 16px rgba(16,185,129,0.25); transform: translateY(-2px); }
.signal-active-sell { background: rgba(239,68,68,0.15); border: 1.5px solid #EF4444; color: #EF4444; box-shadow: 0 0 16px rgba(239,68,68,0.25); transform: translateY(-2px); }
.signal-active-hold { background: rgba(245,158,11,0.15); border: 1.5px solid #F59E0B; color: #F59E0B; box-shadow: 0 0 16px rgba(245,158,11,0.25); transform: translateY(-2px); }
.signal-dim { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); color: #475569; }

/* ── Day Range Bar ── */
.range-bar-wrapper { margin: 6px 0 18px; }
.range-track { height: 6px; border-radius: 3px; background: rgba(255,255,255,0.08); position: relative; margin: 8px 0; overflow: hidden; }
.range-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #EF4444, #F59E0B, #10B981); transition: width 1s ease-out; }
.range-labels { display: flex; justify-content: space-between; font-size: 12px; color: #94A3B8; font-family: 'Roboto Mono', monospace; }

/* ── News Cards ── */
.news-card {
    display: flex; flex-direction: column;
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 12px; padding: 16px; margin-bottom: 12px;
    text-decoration: none !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.news-card:hover { 
    background: rgba(45,61,86,0.7); 
    border-color: rgba(59,130,246,0.4); 
    transform: translateX(6px) scale(1.01); 
    box-shadow: -4px 8px 15px rgba(0,0,0,0.2); 
}
.news-title { color: #F8FAFC; font-size: 15px; font-weight: 600; margin-bottom: 10px; line-height: 1.45; }
.news-meta { display: flex; justify-content: space-between; align-items: center; }
.news-chip { background: linear-gradient(90deg, #1D4ED8, #3B82F6); color: #fff; padding: 3px 10px; border-radius: 4px; font-size: 10px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; box-shadow: 0 2px 4px rgba(59,130,246,0.3); }
.news-time { color: #64748B; font-size: 12px; font-family: 'Roboto Mono', monospace; }

/* ── Agent Section ── */
.summary-quote {
    border-left: 4px solid #3B82F6;
    padding: 16px 20px;
    background: linear-gradient(90deg, rgba(59,130,246,0.08) 0%, transparent 100%);
    border-radius: 0 10px 10px 0;
    color: #E2E8F0;
    font-size: 16px;
    line-height: 1.7;
    margin-bottom: 24px;
}

/* ── Finding Items ── */
.finding-item {
    padding: 14px 16px;
    background: rgba(255,255,255,0.02);
    border-radius: 10px;
    margin-bottom: 8px;
    border-left: 3px solid #3B82F6;
    transition: background 0.2s;
}
.finding-item:hover { background: rgba(59,130,246,0.05); }
.finding-topic { color: #93C5FD; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.finding-detail { color: #CBD5E1; font-size: 14px; line-height: 1.5; }

.risk-item {
    padding: 12px 16px;
    background: rgba(239,68,68,0.03);
    border-radius: 10px;
    margin-bottom: 8px;
    border-left: 3px solid #EF4444;
    color: #CBD5E1; font-size: 14px;
    transition: background 0.2s;
}
.risk-item:hover { background: rgba(239,68,68,0.08); }

/* ── Clean up Streamlit chrome ── */
header, [data-testid="stToolbar"] { visibility: hidden !important; }
div[data-testid="stDecoration"] { display: none; }
div[data-baseweb="input"] { 
    background-color: rgba(15,23,42,0.8) !important; 
    border: 1px solid rgba(255,255,255,0.08) !important; 
    border-radius: 10px; 
    transition: all 0.2s !important;
}
div[data-baseweb="input"]:focus-within { border-color: #3B82F6 !important; box-shadow: 0 0 20px rgba(59,130,246,0.3) !important; transform: scale(1.01); }
input { color: #FFFFFF !important; font-size: 22px !important; font-weight: 700 !important; text-transform: uppercase !important; font-family: 'Roboto Mono', monospace !important; }

button[kind="primary"] {
    background: linear-gradient(90deg, #1D4ED8, #3B82F6) !important;
    border: none !important; border-radius: 10px !important;
    color: white !important; font-weight: 700 !important; font-size: 15px !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    box-shadow: 0 4px 15px rgba(59,130,246,0.3) !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
button[kind="primary"]:hover { box-shadow: 0 8px 25px rgba(59,130,246,0.5) !important; transform: translateY(-2px) scale(1.02) !important; }

/* Tabs customization */
button[data-baseweb="tab"] { color: #94A3B8 !important; font-weight: 600 !important; background: transparent !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #3B82F6 !important; border-bottom-color: #3B82F6 !important; }
</style>
""", unsafe_allow_html=True)

# ── Caching Wrappers (Performance Polish) ─────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_cached_stock(symbol):
    return stock_service.get_full_stock_data(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_hist(symbol, period):
    return stock_service.get_historical_data(symbol, period=period, interval="1d")

@st.cache_data(ttl=900, show_spinner=False)
def get_cached_news(symbol):
    return news_service.get_news_for_symbol(symbol, limit=6)

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_analysis(symbol, _stock_dict, _news_data):
    # LLMs take Pydantic objects, Streamlit cache likes dicts/primitives
    stock_data = StockDataResponse(**_stock_dict)
    return analyst_agent.analyze_stock(stock_data, _news_data)

# ── Helpers ───────────────────────────────────────────────────────────────────

def derive_trading_signal(rsi, price, sma, ema):
    """Derives a simple directional signal from RSI and moving averages."""
    score = 0
    if rsi:
        if rsi < 35: score += 2
        elif rsi > 65: score -= 2
    if price and sma:
        if price > sma: score += 1
        elif price < sma: score -= 1
    if price and ema:
        if price > ema: score += 1
        elif price < ema: score -= 1
    if score >= 2: return "BUY"
    if score <= -2: return "SELL"
    return "HOLD"

def build_rsi_gauge(rsi_value: float) -> go.Figure:
    """Builds an animated Plotly gauge for RSI."""
    color = "#10B981" if rsi_value < 35 else "#EF4444" if rsi_value > 65 else "#F59E0B"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi_value,
        number={'font': {'size': 44, 'color': '#F8FAFC', 'family': 'Roboto Mono'}, 'valueformat': '.1f'},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#334155", 'tickfont': {'color': '#64748B', 'size': 11}},
            'bar': {'color': color, 'thickness': 0.25},
            'bgcolor': 'rgba(255,255,255,0.02)',
            'bordercolor': 'rgba(0,0,0,0)',
            'steps': [
                {'range': [0, 30], 'color': 'rgba(16,185,129,0.15)'},
                {'range': [30, 70], 'color': 'rgba(245,158,11,0.05)'},
                {'range': [70, 100], 'color': 'rgba(239,68,68,0.15)'}
            ],
            'threshold': {'line': {'color': color, 'width': 4}, 'thickness': 0.8, 'value': rsi_value}
        }
    ))
    fig.update_layout(
        height=200, margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor='rgba(0,0,0,0)', font_color='#94A3B8'
    )
    return fig

def build_spark_chart(hist_data: list) -> go.Figure:
    """Builds a minimal sparkline from price history."""
    prices = [r['close'] for r in hist_data[-30:]]  # last 30 days
    color = "#10B981" if prices[-1] >= prices[0] else "#EF4444"
    fig = go.Figure(go.Scatter(
        y=prices, mode='lines', fill='tozeroy',
        line=dict(color=color, width=2.5, shape='spline', smoothing=1.3),
        fillcolor=f"rgba({'16,185,129' if color=='#10B981' else '239,68,68'}, 0.15)",
        hoverinfo='skip'
    ))
    fig.update_layout(
        height=70, margin=dict(l=0,r=0,t=0,b=0),
        xaxis=dict(visible=False, fixedrange=True), 
        yaxis=dict(visible=False, fixedrange=True),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    return fig

def build_main_chart(df: pd.DataFrame, sma: float, ema: float) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.75, 0.25])

    hover_text = []
    for index, row in df.iterrows():
        hover_text.append(f"Date: {row['date'].split(' ')[0]}<br>Open: ${row['open']:.2f}<br>High: ${row['high']:.2f}<br>Low: ${row['low']:.2f}<br>Close: ${row['close']:.2f}")

    fig.add_trace(go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name='Price action',
        increasing=dict(line=dict(color='#10B981', width=1.5), fillcolor='rgba(16,185,129,0.5)'),
        decreasing=dict(line=dict(color='#EF4444', width=1.5), fillcolor='rgba(239,68,68,0.5)'),
        hovertext=hover_text, hoverinfo="text"
    ), row=1, col=1)

    if sma:
        df_sma = df['close'].rolling(20).mean()
        fig.add_trace(go.Scatter(x=df['date'], y=df_sma, name='Hover: SMA 20',
            line=dict(color='#F59E0B', width=2, dash='dash'), hoverinfo='y', hovertemplate="SMA: $%{y:.2f}<extra></extra>"), row=1, col=1)

    if ema:
        df_ema = df['close'].ewm(span=14).mean()
        fig.add_trace(go.Scatter(x=df['date'], y=df_ema, name='Hover: EMA 14',
            line=dict(color='#818CF8', width=2, dash='dot'), hoverinfo='y', hovertemplate="EMA: $%{y:.2f}<extra></extra>"), row=1, col=1)

    vol_colors = ['rgba(239,68,68,0.7)' if r['open'] >= r['close'] else 'rgba(16,185,129,0.7)' for _, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df['date'], y=df['volume'], marker_color=vol_colors, name='Volume', hovertemplate="Vol: %{y:,.0f}<extra></extra>"), row=2, col=1)

    fig.update_layout(
        height=480, margin=dict(l=0,r=0,t=12,b=0),
        plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.04, bgcolor='rgba(0,0,0,0)', font=dict(color='#94A3B8', size=12)),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(15,23,42,0.9)", font_size=13, font_family="Roboto Mono, monospace", bordercolor="rgba(59,130,246,0.5)")
    )
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.03)', tickfont=dict(color='#64748B'), row=1, col=1)
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.03)', tickfont=dict(color='#64748B', family='Roboto Mono'), row=1, col=1)
    fig.update_xaxes(showgrid=False, tickfont=dict(color='#64748B'), row=2, col=1)
    fig.update_yaxes(showgrid=False, showticklabels=False, row=2, col=1)
    return fig


# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-banner animated-card" style="animation-delay: 0s;">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
        <div>
            <h1 class="header-title">⚡ Financial Intelligence Terminal</h1>
            <p class="header-sub">AI-Powered Synthesis &nbsp;|&nbsp; Live Data Streams &nbsp;|&nbsp; Millisecond Caching</p>
        </div>
        <div>
            <div class="market-status">
                <div class="status-dot"></div>
                SYSTEMS ONLINE
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── INPUT ROW ─────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([3, 1.2, 2])
with c1:
    symbol_input = st.text_input("", value="AAPL", placeholder="ENTER TICKER SYMBOL...", label_visibility="collapsed")
with c2:
    st.markdown("<div style='padding-top:4px'></div>", unsafe_allow_html=True)
    analyze_btn = st.button("⚡ EXECUTE SCAN", type="primary", use_container_width=True)

st.markdown("---", unsafe_allow_html=False)

# ── MAIN LOGIC ────────────────────────────────────────────────────────────────
if analyze_btn and symbol_input:
    symbol = symbol_input.upper().strip()
    
    # We use a placeholder so we can wipe the progress bar smoothly
    loading_ph = st.empty()
    
    with loading_ph.container():
        st.markdown("""
        <div style="text-align:center; padding: 40px; color:#64748B;">
            <div class="status-dot" style="display:inline-block; margin-bottom:15px; width:12px; height:12px;"></div>
            <h3 style="color:#94A3B8 !important; font-weight:400;">Bypassing cache, fetching live streams...</h3>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(0.3) # Artificial micro-delay for UX fluidity
        
    try:
        # ── Phase 1: Fetch market data (always works, no LLM) ──────────────────
        stock_dict = get_cached_stock(symbol)
        stock_data = StockDataResponse(**stock_dict)
        news_data = get_cached_news(symbol)

        # ── Phase 2: AI Analysis (graceful degradation on quota error) ──────────
        analysis = None
        analysis_error = None
        try:
            analysis = get_cached_analysis(symbol, stock_dict, news_data)
        except Exception as ae:
            import traceback
            analysis_error = str(ae) + "\\n" + traceback.format_exc()

        # Drop the loading screen instantly
        loading_ph.empty()

        # Derived Values
        signal = derive_trading_signal(stock_data.rsi, stock_data.current_price, stock_data.sma, stock_data.ema)
        delta_v = (stock_data.current_price - stock_data.previous_close) if stock_data.previous_close else 0
        delta_p = (delta_v / stock_data.previous_close * 100) if stock_data.previous_close and stock_data.previous_close != 0 else 0
        delta_cls = "up" if delta_v >= 0 else "down"
        delta_sym = "▲" if delta_v >= 0 else "▼"

        # ─────────────────────────────────────────────────────────────────────
        # ROW 1: Key Metric Row
        # ─────────────────────────────────────────────────────────────────────
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)

        with mc1:
            hist_res_1mo = get_cached_hist(symbol, "1mo")
            sparkfig = build_spark_chart(hist_res_1mo.get("data", [])) if "data" in hist_res_1mo else None
            
            st.markdown(f"""
            <div class="mc animated-card" style="animation-delay: 0.1s;">
                <div class="mc-label">Live Price — {stock_data.symbol} <span id="ws-indicator" style="display:inline-block; width:8px; height:8px; background:#EF4444; border-radius:50%; margin-left:4px;" title="Connecting..."></span></div>
                <div class="mc-value" id="ws-live-price">{stock_data.current_price:,.2f}</div>
                <div class="mc-sub {delta_cls}">{delta_sym} {abs(delta_v):.2f} &nbsp;({abs(delta_p):.2f}%)</div>
            </div>""", unsafe_allow_html=True)
            
            # ── Inject WebSocket JS Client (Bypassing Streamlit Iframe Isolation) ──
            ws_code = f"""
            <script>
                // Wait for the parent document to be ready
                setTimeout(function() {{
                    try {{
                        const doc = window.parent.document;
                        const priceEl = doc.getElementById("ws-live-price");
                        const indEl = doc.getElementById("ws-indicator");
                        if (!priceEl) return;
                        
                        // Use wss:// if hosted, ws:// locally. 
                        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                        // Use localhost:8000 for local dev frontend->backend, or the same host if deployed together
                        const wsUrl = wsProtocol + '//localhost:8000/api/v1/stream/price/{symbol}';
                        
                        const ws = new WebSocket(wsUrl);
                        
                        ws.onopen = function() {{
                            indEl.style.background = '#10B981'; // Green dot = Live
                            indEl.title = 'Live Stream Connected';
                        }};
                        
                        ws.onmessage = function(event) {{
                            const data = JSON.parse(event.data);
                            if (data.price && priceEl) {{
                                const currentParsed = parseFloat(priceEl.innerText.replace(/,/g, ''));
                                const newParsed = parseFloat(data.price);
                                
                                // Flash effect
                                if (newParsed > currentParsed) {{
                                    priceEl.style.color = '#10B981';
                                }} else if (newParsed < currentParsed) {{
                                    priceEl.style.color = '#EF4444';
                                }}
                                
                                // Format number and set
                                priceEl.innerText = newParsed.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
                                
                                // Reset color after 1s
                                setTimeout(() => {{ priceEl.style.color = '#F1F5F9'; }}, 1000);
                            }}
                        }};
                        
                        ws.onclose = function() {{
                            indEl.style.background = '#F59E0B'; // Yellow/Orange = Disconnected
                            indEl.title = 'Stream Disconnected';
                        }};
                    }} catch(e) {{
                        console.error("Streamlit WebSocket injection failed:", e);
                    }}
                }}, 500);
            </script>
            """
            components.html(ws_code, height=0)
            
            if sparkfig:
                st.plotly_chart(sparkfig, use_container_width=True, config={'displayModeBar': False})

        with mc2:
            rsi_cls = "warn"
            rsi_label = "Neutral"
            if stock_data.rsi:
                if stock_data.rsi > 70: rsi_cls, rsi_label = "down", "Overbought"
                elif stock_data.rsi < 30: rsi_cls, rsi_label = "up", "Oversold"
            st.markdown(f"""
            <div class="mc animated-card" style="animation-delay: 0.15s;">
                <div class="mc-label">RSI 14-day</div>
                <div class="mc-value">{f'{stock_data.rsi:.1f}' if stock_data.rsi else 'N/A'}</div>
                <div class="mc-sub {rsi_cls}">{rsi_label}</div>
            </div>""", unsafe_allow_html=True)

        with mc3:
            above_sma = stock_data.current_price > stock_data.sma if stock_data.sma else None
            sma_cls = "up" if above_sma else "down" if above_sma is False else "muted"
            sma_label = "Price Above SMA" if above_sma else "Price Below SMA" if above_sma is False else "N/A"
            st.markdown(f"""
            <div class="mc animated-card" style="animation-delay: 0.2s;">
                <div class="mc-label">SMA 20-day</div>
                <div class="mc-value">{f'{stock_data.sma:,.2f}' if stock_data.sma else 'N/A'}</div>
                <div class="mc-sub {sma_cls}">{sma_label}</div>
            </div>""", unsafe_allow_html=True)

        with mc4:
            st.markdown(f"""
            <div class="mc animated-card" style="animation-delay: 0.25s;">
                <div class="mc-label">Prev. Close</div>
                <div class="mc-value">{f'{stock_data.previous_close:,.2f}' if stock_data.previous_close else 'N/A'}</div>
                <div class="mc-sub muted">Day baseline</div>
            </div>""", unsafe_allow_html=True)

        with mc5:
            sentiment_label = analysis.sentiment if analysis else "N/A"
            st.markdown(f"""
            <div class="mc animated-card" style="border-color:rgba(59,130,246,0.3); animation-delay: 0.3s; background: rgba(59,130,246,0.05);">
                <div class="mc-label" style="color:#93C5FD;">Agent Verdict</div>
                <div style="margin: 12px 0 4px;"><span class="sbadge {sentiment_label}">{sentiment_label}</span></div>
            </div>""", unsafe_allow_html=True)


        # ROW 2: Day Range + Trading Signal Row
        # ─────────────────────────────────────────────────────────────────────
        low = stock_data.day_low or 0
        high = stock_data.day_high or 0
        curr = stock_data.current_price
        fill_pct = max(0, min(100, ((curr - low) / (high - low) * 100))) if (high - low) > 0 else 50
        buy_cls  = "signal-active-buy"  if signal == "BUY"  else "signal-dim"
        hold_cls = "signal-active-hold" if signal == "HOLD" else "signal-dim"
        sell_cls = "signal-active-sell" if signal == "SELL" else "signal-dim"

        sig_r, _ = st.columns([3, 1])
        with sig_r:
            st.markdown(f"""
            <div class="glass-card animated-card" style="animation-delay: 0.35s;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="color:#94A3B8; font-size:13px; letter-spacing:1px; font-weight:600; text-transform:uppercase;">Intraday Range</span>
                    <span style="color:#64748B; font-size:12px; font-family:'Roboto Mono',monospace;">Day Low · Current · Day High</span>
                </div>
                <div class="range-track">
                    <div class="range-fill" style="width:{fill_pct:.1f}%;"></div>
                </div>
                <div class="range-labels">
                    <span>&#8595; {stock_data.currency} {low:,.2f}</span>
                    <span style="color:#F8FAFC; font-weight:600;">CURR {stock_data.currency} {curr:,.2f}</span>
                    <span>{stock_data.currency} {high:,.2f} &#8593;</span>
                </div>
                <div class="signals-row">
                    <div class="signal-chip {buy_cls}">📈 &nbsp; BUY Signal {' ⬅' if signal=='BUY' else ''}</div>
                    <div class="signal-chip {hold_cls}">⏸ &nbsp; HOLD Signal {' ⬅' if signal=='HOLD' else ''}</div>
                    <div class="signal-chip {sell_cls}">📉 &nbsp; SELL Signal {' ⬅' if signal=='SELL' else ''}</div>
                </div>
                <p style="color:#475569; font-size:11px; margin: 0; text-align:center;">
                    Directional signal algorithmically derived from RSI momentum and Moving Average crossovers.
                </p>
            </div>
            """, unsafe_allow_html=True)


        # ─────────────────────────────────────────────────────────────────────
        # ROW 3: Advanced Chart (Tabs) + RSI Gauge + News
        # ─────────────────────────────────────────────────────────────────────
        chart_col, gauge_col, news_col = st.columns([3, 1, 1.5])

        with chart_col:
            st.markdown('<div class="glass-card animated-card" style="padding:16px; animation-delay: 0.4s;">', unsafe_allow_html=True)
            
            # Interactive Chart Tabs
            t1, t2, t3 = st.tabs(["1 Month", "3 Month", "6 Month"])
            
            with t1:
                hist_1mo = get_cached_hist(symbol, "1mo")
                if "data" in hist_1mo and hist_1mo["data"]:
                    st.plotly_chart(build_main_chart(pd.DataFrame(hist_1mo["data"]), stock_data.sma, stock_data.ema), use_container_width=True, config={'displayModeBar': False})
            with t2:
                hist_3mo = get_cached_hist(symbol, "3mo")
                if "data" in hist_3mo and hist_3mo["data"]:
                    st.plotly_chart(build_main_chart(pd.DataFrame(hist_3mo["data"]), stock_data.sma, stock_data.ema), use_container_width=True, config={'displayModeBar': False})
            with t3:
                hist_6mo = get_cached_hist(symbol, "6mo")
                if "data" in hist_6mo and hist_6mo["data"]:
                    st.plotly_chart(build_main_chart(pd.DataFrame(hist_6mo["data"]), stock_data.sma, stock_data.ema), use_container_width=True, config={'displayModeBar': False})
                    
            st.markdown('</div>', unsafe_allow_html=True)

        with gauge_col:
            st.markdown('<div class="glass-card animated-card" style="text-align:center; animation-delay: 0.45s;">', unsafe_allow_html=True)
            st.markdown("<p style='color:#94A3B8; font-size:11px; text-transform:uppercase; letter-spacing:1.5px; font-weight:600; margin-bottom:0;'>RSI Gauge</p>", unsafe_allow_html=True)
            if stock_data.rsi:
                st.plotly_chart(build_rsi_gauge(stock_data.rsi), use_container_width=True, config={'displayModeBar': False})
                zone = "🔴 OVERBOUGHT" if stock_data.rsi > 70 else "🟢 OVERSOLD" if stock_data.rsi < 30 else "🟡 NEUTRAL"
                st.markdown(f"<p style='font-size:12px; font-weight:700; text-align:center; color:#CBD5E1;'>{zone}</p>", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:20px 0;'>", unsafe_allow_html=True)
            st.markdown(f"""
            <p style='color:#94A3B8; font-size:11px; text-transform:uppercase; letter-spacing:1.5px; font-weight:600;'>EMA 14-Day</p>
            <p style='color:#818CF8; font-size:28px; font-weight:700; font-family:Roboto Mono,monospace; margin:4px 0;'>{f'{stock_data.ema:,.2f}' if stock_data.ema else 'N/A'}</p>
            <p style='color:#475569; font-size:11px;'>Exponential Moving Avg</p>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with news_col:
            st.markdown('<div class="glass-card animated-card" style="padding:16px; animation-delay: 0.5s;">', unsafe_allow_html=True)
            st.markdown("<p style='color:#F1F5F9; font-size:14px; font-weight:700; text-transform:uppercase; letter-spacing:1px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom:10px; margin-bottom:14px;'>📰 Live Market Context</p>", unsafe_allow_html=True)
            if news_data.count > 0:
                for a in news_data.articles:
                    pub = a.published_at.strftime('%b %d %H:%M') if a.published_at else ''
                    st.markdown(f"""
                    <a href="{a.url}" target="_blank" class="news-card">
                        <div class="news-title">{a.title}</div>
                        <div class="news-meta">
                            <span class="news-chip">{a.source.upper() if a.source else 'WEB'}</span>
                            <span class="news-time">{pub}</span>
                        </div>
                    </a>""", unsafe_allow_html=True)
            else:
                st.info("No news found for this symbol.")
            st.markdown('</div>', unsafe_allow_html=True)


        # ─────────────────────────────────────────────────────────────────────
        # ROW 4: AI Intelligence Panel
        # ─────────────────────────────────────────────────────────────────────
        st.markdown('<div class="glass-card animated-card" style="animation-delay: 0.6s;">', unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#E2E8F0; margin-bottom:14px;'>🧠 Intelligence Report — <span style='color:#3B82F6;font-family:Roboto Mono,monospace;'>{symbol}</span></h3>", unsafe_allow_html=True)

        if analysis:
            st.markdown(f'<div class="summary-quote">{analysis.summary}</div>', unsafe_allow_html=True)
            kf_col, rf_col = st.columns(2)
            with kf_col:
                st.markdown("<p style='color:#94A3B8; font-size:12px; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:12px;'>🔑 Key Findings</p>", unsafe_allow_html=True)
                for f in analysis.key_findings:
                    st.markdown(f"""
                    <div class="finding-item">
                        <div class="finding-topic">{f.topic}</div>
                        <div class="finding-detail">{f.detail}</div>
                    </div>""", unsafe_allow_html=True)
            with rf_col:
                st.markdown("<p style='color:#94A3B8; font-size:12px; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:12px;'>⚠️ Risk Factors</p>", unsafe_allow_html=True)
                for r in analysis.risk_factors:
                    st.markdown(f'<div class="risk-item">{r}</div>', unsafe_allow_html=True)
                st.markdown("<p style='color:#94A3B8; font-size:12px; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-top:20px; margin-bottom:12px;'>📐 Technical Posture</p>", unsafe_allow_html=True)
                st.markdown(f'<div class="finding-item" style="border-left-color:#818CF8;"><div class="finding-detail">{analysis.technical_posture}</div></div>', unsafe_allow_html=True)
        else:
            err_detail = analysis_error or "Unknown error — check terminal logs."
            st.markdown(f"""
            <div style="padding:20px; background:rgba(251,191,36,0.08); border:1px solid rgba(251,191,36,0.3); border-radius:12px; text-align:center;">
                <div style="font-size:32px;">⏳</div>
                <p style="color:#FCD34D; font-weight:600; margin:8px 0;">AI Analysis Temporarily Unavailable</p>
                <p style="color:#94A3B8; font-size:13px; margin:0; font-family:monospace;">{err_detail}</p>
                <p style="color:#64748B; font-size:12px; margin-top:8px;">Stock prices, charts, and news above are fully available.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        loading_ph.empty()
        st.markdown(f"""
        <div class="animated-card" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239,68,68,0.3); padding: 24px; border-radius: 14px; animation-delay: 0s;">
        <h3 style="color: #EF4444 !important; margin-top: 0;">❌ Pipeline Execution Failed</h3>
        <p style="color:#F8FAFC;">{str(e)}</p>
        </div>""", unsafe_allow_html=True)

elif not analyze_btn:
    st.markdown("""
    <div class="animated-card" style="display:flex; flex-direction:column; justify-content:center; align-items:center;
                height: 55vh; text-align:center; color:#1E293B; animation-delay:0s;">
        <div style="font-size:80px; margin-bottom:20px; filter: drop-shadow(0 0 30px rgba(59,130,246,0.3));">⚡</div>
        <h2 style="color:#64748B !important; font-weight:300; font-size:28px; margin-bottom:10px;">System Online & Ready</h2>
        <p style="color:#475569; font-family:'Roboto Mono',monospace;">Enter a ticker symbol above and click EXECUTE SCAN to initiate.</p>
    </div>
    """, unsafe_allow_html=True)
