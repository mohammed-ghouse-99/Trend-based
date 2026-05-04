import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

from project.app.login import show_login
from project.app.ui_utils import load_css, render_decision_banner, render_halal_scorecard

st.set_page_config(
    page_title="Trend-Based Halal Stock Prediction System",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# AUTH SESSION
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# LOGIN PROTECTION
if not st.session_state["authenticated"]:
    show_login()
    st.stop()

# --------------------------------------------------------------------
# PATH FIX so that "project.*" imports work even when run from root
# --------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from project.data.collector import get_data
from project.data.storage import load_cache, save_cache
from project.data.processor import add_indicators
from project.core.trend_detector import TrendDetector
from project.core.renku import RenkoDetector
from project.visual.charts import (
    plot_candlestick,
    plot_rsi,
    plot_macd,
    plot_volume,
    plot_renko,
    plot_integrated_terminal,
    render_price_chart,
)
from project.core.halal.pipeline import screen_stock

# Path to trained model (created by project/main.py)
MODEL_PATH = "project/models/model.pkl"

# --------------------------------------------------------------------
# ░░░  ELITE CSS — APEX TRADING TERMINAL  ░░░
# --------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&display=swap');

/* ── ROOT ─────────────────────────────────────────── */
:root {
  --ink:       #060910;
  --surface:   #0b0f1a;
  --panel:     #0f1623;
  --panel2:    #131c2e;
  --border:    rgba(201,168,76,0.14);
  --border2:   rgba(255,255,255,0.05);
  --gold:      #c9a84c;
  --gold-lt:   #e8c97a;
  --gold-dim:  rgba(201,168,76,0.08);
  --green:     #10b981;
  --green-dim: rgba(16,185,129,0.15);
  --red:       #ef4444;
  --red-dim:   rgba(239,68,68,0.15);
  --amber:     #f59e0b;
  --text:      #e2e8f0;
  --muted:     #4a5568;
  --muted2:    #6b7280;
  --mono:      'DM Mono', monospace;
  --display:   'Syne', sans-serif;
}

/* ── GLOBAL RESET ─────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
#MainMenu, footer, header { visibility: hidden; }

.stApp {
  background: var(--ink);
  font-family: var(--display);
  color: var(--text);
}

/* subtle animated grid */
.stApp::before {
  content: '';
  position: fixed; inset: 0;
  background-image:
    linear-gradient(rgba(201,168,76,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(201,168,76,0.025) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: gridScroll 40s linear infinite;
  pointer-events: none; z-index: 0;
}
@keyframes gridScroll {
  from { background-position: 0 0; }
  to   { background-position: 60px 60px; }
}

.main .block-container {
  padding: 1.5rem 2rem 3rem;
  max-width: 1600px;
  position: relative; z-index: 1;
}

/* ── TOP HEADER BAR ───────────────────────────────── */
.apex-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  border-radius: 0 0 16px 16px;
  margin: -1.5rem -2rem 2rem;
  box-shadow: 0 4px 40px rgba(0,0,0,0.6);
}
.apex-brand {
  display: flex; align-items: center; gap: 12px;
}
.apex-hex {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, var(--gold), var(--gold-lt));
  clip-path: polygon(50% 0%,93% 25%,93% 75%,50% 100%,7% 75%,7% 25%);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  box-shadow: 0 0 20px rgba(201,168,76,0.5);
  animation: hexPulse 3s ease-in-out infinite;
}
@keyframes hexPulse {
  0%,100% { box-shadow: 0 0 16px rgba(201,168,76,0.4); }
  50%      { box-shadow: 0 0 32px rgba(201,168,76,0.75); }
}
.apex-wordmark {
  font-size: 20px; font-weight: 800;
  letter-spacing: -0.02em; color: var(--text);
}
.apex-wordmark span {
  background: linear-gradient(135deg, var(--gold), var(--gold-lt));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.apex-tagline {
  font-family: var(--mono);
  font-size: 10px; color: var(--muted);
  letter-spacing: 0.14em; text-transform: uppercase;
}
.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
  animation: blink 1.8s ease-in-out infinite;
  display: inline-block; margin-right: 6px;
}
@keyframes blink {
  0%,100% { opacity:1; } 50% { opacity:0.25; }
}
.header-right {
  font-family: var(--mono);
  font-size: 11px; color: var(--muted2);
  display: flex; align-items: center; gap: 6px;
}

/* ── SECTION LABEL ────────────────────────────────── */
.section-label {
  font-family: var(--mono);
  font-size: 10px; font-weight: 500;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 10px;
  display: flex; align-items: center; gap: 8px;
}
.section-label::after {
  content: ''; flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--border), transparent);
}

/* ── INPUT PANEL ──────────────────────────────────── */
.input-panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
}

/* ── INPUT OVERRIDES ──────────────────────────────── */
.stTextInput > div > div > input {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  letter-spacing: 0.06em !important;
  padding: 11px 14px !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px rgba(201,168,76,0.1) !important;
  outline: none !important;
}
.stTextInput label { color: var(--muted2) !important; font-size: 11px !important; letter-spacing: 0.1em; text-transform: uppercase; font-family: var(--mono) !important; }
.stTextInput > div > div > input::placeholder { color: var(--muted) !important; }

.stSelectbox > div > div {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
}
.stSelectbox label { color: var(--muted2) !important; font-size: 11px !important; letter-spacing: 0.1em; text-transform: uppercase; font-family: var(--mono) !important; }

.stCheckbox > label { color: var(--muted2) !important; font-family: var(--mono) !important; font-size: 12px !important; }

/* ── BUTTON ───────────────────────────────────────── */
.stButton > button {
  background: linear-gradient(135deg, #a07828 0%, var(--gold-lt) 50%, #a07828 100%) !important;
  background-size: 200% 100% !important;
  color: var(--ink) !important;
  font-family: var(--display) !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  border: none !important;
  border-radius: 10px !important;
  height: 46px !important;
  transition: background-position 0.4s, transform 0.15s, box-shadow 0.15s !important;
  box-shadow: 0 4px 20px rgba(201,168,76,0.3) !important;
}
.stButton > button:hover {
  background-position: 100% 0 !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 28px rgba(201,168,76,0.5) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── COMPANY HEADER ───────────────────────────────── */
.company-header {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px 28px;
  margin-bottom: 20px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);
  position: relative; overflow: hidden;
}
.company-header::before {
  content: '';
  position: absolute; top: 0; left: 0;
  width: 4px; height: 100%;
  background: linear-gradient(180deg, var(--gold), transparent);
  border-radius: 16px 0 0 16px;
}
.company-name {
  font-size: 26px; font-weight: 800;
  color: white; margin-bottom: 4px;
  letter-spacing: -0.02em;
}
.company-meta {
  color: var(--muted2);
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}
.price-container {
  display: flex; align-items: baseline; gap: 14px; margin-top: 6px;
}
.price-main {
  font-size: 38px; font-weight: 800;
  font-family: var(--mono);
  color: white; letter-spacing: -0.02em;
}
.price-change {
  font-size: 15px; font-weight: 600;
  padding: 5px 14px; border-radius: 20px;
  font-family: var(--mono);
  background: var(--green-dim);
  color: var(--green);
  border: 1px solid rgba(16,185,129,0.25);
}
.price-down {
  background: var(--red-dim) !important;
  color: var(--red) !important;
  border-color: rgba(239,68,68,0.25) !important;
}

/* ── RIGHT SIDE ANALYSIS CARDS ────────────────────── */
.analysis-panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  height: 100%;
  box-shadow: 0 8px 40px rgba(0,0,0,0.5);
}
.card-section-title {
  font-family: var(--mono);
  font-size: 10px; font-weight: 500;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--gold);
  margin: 0 0 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 6px;
}
.card-divider {
  height: 1px;
  background: var(--border);
  margin: 16px 0;
}

/* ── ALERT OVERRIDES ──────────────────────────────── */
.stSuccess, .stError, .stWarning, .stInfo {
  border-radius: 10px !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
  border: none !important;
}
.stSuccess { background: var(--green-dim) !important; color: var(--green) !important; border-left: 3px solid var(--green) !important; }
.stError   { background: var(--red-dim)   !important; color: var(--red)   !important; border-left: 3px solid var(--red)   !important; }
.stWarning { background: rgba(245,158,11,0.12) !important; color: var(--amber) !important; border-left: 3px solid var(--amber) !important; }
.stInfo    { background: rgba(59,130,246,0.1)  !important; color: #60a5fa !important; border-left: 3px solid #3b82f6 !important; }

/* ── GAUGE CONTAINER ──────────────────────────────── */
.gauge-container {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  transition: transform 0.2s, box-shadow 0.2s;
}
.gauge-container:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(201,168,76,0.12);
}
.gauge-label {
  font-family: var(--mono);
  font-size: 11px; color: var(--muted2);
  text-align: center; margin-top: 4px;
  letter-spacing: 0.08em;
}

/* ── TABLES ───────────────────────────────────────── */
.stDataFrame {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}
.stDataFrame th {
  background: var(--panel2) !important;
  color: var(--gold-lt) !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  border-bottom: 1px solid var(--border) !important;
}
.stDataFrame td {
  background: var(--panel) !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
  border-bottom: 1px solid rgba(255,255,255,0.03) !important;
}
.stDataFrame tr:hover td { background: var(--panel2) !important; }

/* ── TABS ─────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  background: var(--panel) !important;
  border-radius: 12px !important;
  padding: 6px !important;
  border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 8px !important;
  color: var(--muted2) !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  letter-spacing: 0.08em !important;
  padding: 8px 20px !important;
  transition: all 0.2s !important;
  border: none !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text) !important; background: var(--panel2) !important; }
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(201,168,76,0.2), rgba(201,168,76,0.08)) !important;
  color: var(--gold-lt) !important;
  border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab-panel"] {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 12px 12px 12px !important;
  padding: 24px !important;
  margin-top: 2px !important;
}

/* ── METRICS ──────────────────────────────────────── */
.stMetric {
  background: var(--panel2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 16px !important;
  transition: transform 0.2s !important;
}
.stMetric:hover { transform: translateY(-2px); }
.stMetric label { color: var(--muted2) !important; font-family: var(--mono) !important; font-size: 11px !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; }
.stMetric [data-testid="metric-container"] > div:nth-child(2) { color: var(--gold-lt) !important; font-family: var(--mono) !important; font-size: 24px !important; font-weight: 500 !important; }

/* ── EXPANDERS ────────────────────────────────────── */
.streamlit-expanderHeader {
  background: var(--panel2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--muted2) !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
  letter-spacing: 0.08em !important;
}
.streamlit-expanderContent {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 10px 10px !important;
}

/* ── SPINNER ──────────────────────────────────────── */
.stSpinner > div { border-top-color: var(--gold) !important; }

/* ── TICKER QUICK PICK BUTTONS ────────────────────── */
.ticker-btn .stButton > button {
  background: var(--panel2) !important;
  color: var(--gold) !important;
  border: 1px solid var(--border) !important;
  box-shadow: none !important;
  font-size: 13px !important;
  height: 40px !important;
}
.ticker-btn .stButton > button:hover {
  background: var(--gold-dim) !important;
  border-color: var(--gold) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 12px rgba(201,168,76,0.2) !important;
}

/* ── SECTION DIVIDER ──────────────────────────────── */
hr { border-color: var(--border) !important; margin: 28px 0 !important; }

/* ── CAPTION / SMALL TEXT ─────────────────────────── */
.stCaption { color: var(--muted2) !important; font-family: var(--mono) !important; font-size: 11px !important; }
p, li { color: var(--text); }
h1,h2,h3,h4 { font-family: var(--display) !important; color: var(--text) !important; }

/* ── SCROLLBAR ────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--ink); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--gold); }

/* ── FADE IN ANIMATION ────────────────────────────── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeUp 0.5s cubic-bezier(0.16,1,0.3,1) both; }
</style>
""", unsafe_allow_html=True)

# ── HEADER BAR ──────────────────────────────────────────────────────
now_str = datetime.now().strftime("%d %b %Y  %H:%M")
st.markdown(f"""
<div class="apex-header fade-in">==
  <div class="apex-brand">
    <div class="apex-hex">⬡</div>
    <div>
      <div class="apex-wordmark">Trend-Based<span></span> Halal Stock Prediction System</div>
    </div>
  </div>
  <div class="header-right">
    <span class="live-dot"></span>
    LIVE &nbsp;·&nbsp; {now_str} IST
  </div>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------
# INPUT BAR
# --------------------------------------------------------------------
st.markdown('<div class="section-label">⬡ &nbsp;Market Parameters</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns([1.4, 1, 1, 1.2, 0.9, 0.9, 1.0])

with col1:
    ticker = st.text_input("Ticker", value="AAPL").upper()
with col2:
    period = st.selectbox("Data for Stock Prediction", ["1y", "2y", "3y", "5y", "max"], index=2)
with col3:
    interval = st.selectbox("Candle Interval", ["1d", "1h", "30m"], index=0)
with col4:
    trend_period = st.selectbox(
        "Data for Trend Detection", ["6mo", "1y", "2y"], index=1,
        help="Used ONLY for market structure (HH/HL, LH/LL)"
    )
with col5:
    use_cache = st.checkbox("Use Cache", value=True)
with col6:
    refresh = st.checkbox("Force Fresh Download")
with col7:
    check_halal = st.checkbox("Halal Screen", value=True)

analyze = st.button("⬡  Analyze", width="stretch", type="primary")

# --------------------------------------------------------------------
# HELPERS: DATA / MODEL  (UNCHANGED LOGIC)
# --------------------------------------------------------------------
def load_or_fetch(ticker: str, period: str, interval: str, use_cache: bool, refresh: bool):
    if use_cache and not refresh:
        cached = load_cache(ticker, period, interval)
        if cached is not None and not cached.empty:
            return cached
    df = get_data(ticker, period, interval)
    if df is None or df.empty:
        st.error("⬡ No data returned. Check ticker or internet.")
        return None
    save_cache(df, ticker, period, interval)
    return df

def get_company_info(ticker_symbol: str):
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        return {
            'name': info.get('longName', ticker_symbol),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'exchange': info.get('exchange', 'N/A'),
            'logo_url': info.get('logo_url', ''),
            'website': info.get('website', ''),
            'summary': info.get('longBusinessSummary', ''),
            'market_cap': info.get('marketCap'),
            'country': info.get('country', 'N/A')
        }
    except Exception:
        return {'name': ticker_symbol, 'sector':'N/A','industry':'N/A','exchange':'N/A',
                'logo_url':'','website':'','summary':'','market_cap':None,'country':'N/A'}

def load_trained_model(model_path: str):
    if not os.path.exists(model_path):
        return None, None
    loaded = joblib.load(model_path)
    if isinstance(loaded, dict) and "model" in loaded:
        return loaded["model"], loaded.get("features", None)
    return loaded, None

# --------------------------------------------------------------------
# TECHNICAL SUMMARY HELPERS  (UNCHANGED LOGIC)
# --------------------------------------------------------------------
RSI_BUY = 30; RSI_SELL = 70
STRONG_MULTIPLIER = 1.02; STRONG_MACD_STD_MULT = 1.5

def action_from_rsi(val):
    if np.isnan(val): return "N/A"
    if val < RSI_BUY: return "Buy"
    if val > RSI_SELL: return "Sell"
    return "Neutral"

def action_from_macd_hist(val, hist_std):
    if np.isnan(val): return "N/A"
    if val > 0: return "Strong Buy" if abs(val)>(STRONG_MACD_STD_MULT*max(hist_std,1e-9)) else "Buy"
    if val < 0: return "Strong Sell" if abs(val)>(STRONG_MACD_STD_MULT*max(hist_std,1e-9)) else "Sell"
    return "Neutral"

def action_from_momentum(val):
    if np.isnan(val): return "N/A"
    return "Buy" if val>0 else ("Sell" if val<0 else "Neutral")

def action_from_return(val):
    if np.isnan(val): return "N/A"
    return "Buy" if val>0 else ("Sell" if val<0 else "Neutral")

def action_from_ma(price, ma):
    if np.isnan(ma) or np.isnan(price): return "N/A"
    if price > ma*STRONG_MULTIPLIER: return "Strong Buy"
    if price > ma: return "Buy"
    if price < ma/STRONG_MULTIPLIER: return "Strong Sell"
    if price < ma: return "Sell"
    return "Neutral"

def aggregate_counts(actions):
    cnt = {"Strong Buy":0,"Buy":0,"Neutral":0,"Sell":0,"Strong Sell":0,"N/A":0}
    for a in actions:
        cnt[a if a in cnt else "N/A"] += 1
    return cnt

ACTION_TO_VAL = {"Strong Sell":10,"Sell":30,"Neutral":50,"Buy":70,"Strong Buy":90,"N/A":50}

def make_gauge(title, action_value, subtitle=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=action_value,
        number={"suffix":"","font":{"size":24,"color":"white"}},
        title={"text":title,"font":{"size":15,"color":"#e8c97a"}},
        gauge={
            "axis":{"range":[0,100],"visible":False},
            "bar":{"color":"white","thickness":0.18},
            "bgcolor":"rgba(0,0,0,0)","borderwidth":0,
            "steps":[
                {"range":[0,20],"color":"#7f1d1d"},
                {"range":[20,40],"color":"#dc2626"},
                {"range":[40,60],"color":"#374151"},
                {"range":[60,80],"color":"#059669"},
                {"range":[80,100],"color":"#10b981"},
            ],
            "threshold":{"line":{"color":"#e8c97a","width":3},"thickness":0.75,"value":action_value},
            "shape":"angular"
        },
        domain={"x":[0,1],"y":[0,1]},
        delta={"reference":50,"increasing":{"color":"#10b981"},"decreasing":{"color":"#ef4444"}},
    ))
    fig.update_layout(
        margin=dict(l=10,r=10,t=40,b=10), height=220,
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
        plot_bgcolor="rgba(0,0,0,0)"
    )
    if subtitle:
        fig.add_annotation(text=subtitle, x=0.5, y=-0.05, showarrow=False,
                           font=dict(size=10, color="#6b7280"))
    return fig

# --------------------------------------------------------------------
# MAIN ACTION: Analyze  (ALL LOGIC PRESERVED)
# --------------------------------------------------------------------
if analyze:
    with st.spinner("⬡ Processing market data…"):

        company_info = get_company_info(ticker)

        df_raw = load_or_fetch(ticker, period, interval, use_cache, refresh)
        if df_raw is None:
            st.stop()

        df_proc = add_indicators(df_raw.copy(), dropna=True)
        if "Adj Close" not in df_proc.columns:
            df_proc["Adj Close"] = df_proc["Close"]

        renko_detector = RenkoDetector(brick_size_method="atr")
        renko_result = renko_detector.detect_trend(df_raw)
        try:
            renko_bricks = renko_detector.bricks
        except AttributeError:
            renko_bricks = []
        renko_brick_size   = renko_result.get('brick_size', 0)
        renko_trend        = renko_result.get('trend', 'UNKNOWN')
        renko_confidence   = renko_result.get('confidence', 0)
        renko_total_bricks = renko_result.get('total_bricks', 0)
        renko_up_bricks    = renko_result.get('up_bricks', 0)
        renko_down_bricks  = renko_result.get('down_bricks', 0)

        try:
            latest = df_proc.iloc[-1]; prev = df_proc.iloc[-2] if len(df_proc)>1 else latest
            last_close = float(latest["Close"]); prev_close = float(prev["Close"])
            change = last_close - prev_close
            change_pct = (change/prev_close*100) if prev_close!=0 else 0.0
            is_positive = change > 0
        except Exception:
            last_close=change=change_pct=0; is_positive=True

        # ── 1. DECISION SYNTHESIS ──────────────────────────────────
        # Process Halal first as it is the primary filter
        halal_res = screen_stock(ticker, use_cache=use_cache)
        h_status = halal_res.get("status", "ERROR")
        
        # Process Technicals
        TREND_PERIOD_MAP = {"6mo":126,"1y":252,"2y":504}
        lookback_bars = TREND_PERIOD_MAP.get(trend_period, 252)
        detector = TrendDetector(lookback=lookback_bars)
        trend_result = detector.detect_trend(df_proc)
        trend = trend_result.get("trend") if trend_result else "UNKNOWN"
        
        # Process ML
        ml_pred = 0; ml_conf = 0.0
        model, feature_list = load_trained_model(MODEL_PATH)
        if model and feature_list:
             try:
                latest_features = df_proc.tail(1)[feature_list].astype(float)
                ml_pred = int(model.predict(latest_features)[0])
                try: proba = model.predict_proba(latest_features)[0]; ml_conf = float(proba.max())
                except: ml_conf = 1.0
             except: pass
        
        # ── 2. RENDER TOP-LEVEL DECISION ───────────────────────────
        render_decision_banner(h_status, trend, ml_pred)

        # ── 2b. CONSOLIDATED CHART CONFIG ──────────────────────────
        CHART_CONFIG = {
            "scrollZoom": True,
            "displayModeBar": False,
            "showAxisDragHandles": True,
            "responsive": True
        }

    # ── 3. MAIN DASHBOARD CONTENT ──────────────────────────────────
    left_col, right_col = st.columns([2.3, 1])

    with left_col:
        # Company Info Header
        header_bg = "var(--panel)"
        if company_info['logo_url']:
            st.markdown(f"""
            <div style="display:flex;align-items:center;margin-bottom:24px; background: {header_bg}; padding: 20px; border-radius: 16px; border: 1px solid var(--border);">
              <img src="{company_info['logo_url']}"
                   style="width:64px;height:64px;border-radius:12px;
                          margin-right:20px;border:1px solid var(--border2);
                          background:white;padding:4px;">
              <div>
                <div class="company-name" style="font-size: 32px; font-weight: 800;">{company_info['name']}</div>
                <div class="company-meta" style="font-size: 14px; color: var(--muted2);">
                  <span style="color:var(--gold); font-weight: 600;">{company_info['exchange']}</span> &nbsp;·&nbsp; {company_info['sector']} &nbsp;·&nbsp; {company_info['country']}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: {header_bg}; padding: 20px; border-radius: 16px; border: 1px solid var(--border); margin-bottom: 24px;">
                <div class="company-name" style="font-size: 32px; font-weight: 800;">{company_info['name']}</div>
                <div class="company-meta" style="font-size: 14px; color: var(--muted2);">
                  <span style="color:var(--gold); font-weight: 600;">{company_info['exchange']}</span> &nbsp;·&nbsp; {company_info['sector']} &nbsp;·&nbsp; {company_info['country']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Price Header
        change_class = "price-change" if is_positive else "price-change price-down"
        sign = "+" if change > 0 else ""
        st.markdown(f"""
        <div class="price-container" style="margin-bottom: 24px;">
          <span class="price-main" style="font-size: 48px;">{last_close:,.2f}</span>
          <span class="{change_class}" style="font-size: 18px;">{sign}{change:+.2f} ({sign}{change_pct:+.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)

        # Main Charts
        CHART_CONFIG = {'displayModeBar': False, 'scrollZoom': False}
        
        try:
            fig_price = plot_candlestick(df_proc)
            st.plotly_chart(fig_price, width="stretch", config=CHART_CONFIG)
        except Exception as e:
            st.error(f"Chart Error: {e}")

        with st.expander("⬡  Audit Metadata & Raw Source", expanded=False):
            st.dataframe(df_raw, width="stretch")
            st.caption(f"Strategy Lookback: {lookback_bars} bars | Interval: {interval}")

    with right_col:
        # Halal Section
        if check_halal:
            render_halal_scorecard(halal_res)
            
            with st.expander("⚠️ Audit Notes", expanded=False):
                violations = halal_res.get("violations", [])
                for v in violations: st.error(f"Fail: {v}")
                notes_list = halal_res.get("notes", [])
                for n in notes_list: st.info(f"Note: {n}")
                st.caption(f"Completeness: {halal_res.get('data_completeness', 0.0):.0%}")
        
        st.markdown('<div class="card-divider"></div>', unsafe_allow_html=True)

        # Technical Signals
        st.markdown('<div class="card-section-title">⬡ &nbsp;Market context</div>', unsafe_allow_html=True)
        
        # Trend
        if trend == "UPTREND": 
            st.success(f"▲ BULLISH SIGNAL (Conf: {trend_result.get('confidence', 0):.2f})")
        elif trend == "DOWNTREND":
            st.error(f"▼ BEARISH SIGNAL (Conf: {trend_result.get('confidence', 0):.2f})")
        else:
            st.warning(f"◆ NEUTRAL / SIDEWAYS")

        # ML
        if ml_pred == 1:
            st.success(f"🚀 ML: UP PROBABILITY ({ml_conf:.0%})")
        else:
            st.info(f"⚖️ ML: NO UP SIGNAL ({ml_conf:.0%})")

        # Renko
        if renko_trend == "UPTREND":
            st.success(f"🧱 RENKO: {renko_total_bricks} UP BRICKS")
        elif renko_trend == "DOWNTREND":
            st.error(f"🧱 RENKO: {renko_total_bricks} DOWN BRICKS")

        st.markdown('<div class="card-divider"></div>', unsafe_allow_html=True)
        
        # Quick Stats Card
        st.markdown(f"""
        <div style="background: var(--panel2); border: 1px solid var(--border); border-radius: 12px; padding: 16px;">
            <div style="font-family: var(--mono); font-size: 10px; color: var(--muted2); margin-bottom: 8px; text-transform: uppercase;">Volume Profile</div>
            <div style="font-size: 18px; font-weight: 600; color: white;">{int(df_proc.iloc[-1]["Volume"]):,}</div>
            <div style="color: var(--muted2); font-size: 11px; margin-top: 4px;">24h Turnover</div>
        </div>
        """, unsafe_allow_html=True)


    # ── TECHNICAL SUMMARY ──────────────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">⬡ &nbsp;Technical Summary</div>', unsafe_allow_html=True)

    last = df_proc.iloc[-1]
    close_price = float(last["Close"]) if "Close" in last else np.nan
    macd_std = df_proc["MACD_HIST"].std() if "MACD_HIST" in df_proc.columns else 0.0

    osc_items=[]; osc_actions=[]
    if "RSI_14" in df_proc.columns:
        v=float(last["RSI_14"]); a=action_from_rsi(v)
        osc_items.append(("RSI (14)",v,a)); osc_actions.append(a)
    if "MACD_HIST" in df_proc.columns:
        v=float(last["MACD_HIST"]); a=action_from_macd_hist(v,macd_std)
        osc_items.append(("MACD Histogram",v,a)); osc_actions.append(a)
    for mcol,label in [("MOMENTUM_5","Momentum (5)"),("MOMENTUM_10","Momentum (10)")]:
        if mcol in df_proc.columns:
            v=float(last[mcol]); a=action_from_momentum(v)
            osc_items.append((label,v,a)); osc_actions.append(a)
    if "RETURNS" in df_proc.columns:
        v=float(last["RETURNS"]); a=action_from_return(v)
        osc_items.append(("Returns",v,a)); osc_actions.append(a)
    if not osc_items:
        osc_items.append(("No oscillators",np.nan,"N/A")); osc_actions.append("N/A")

    ma_items=[]; ma_actions=[]
    for col,label in [("SMA_10","SMA 10"),("SMA_20","SMA 20"),("SMA_50","SMA 50"),
                       ("SMA_200","SMA 200"),("EMA_10","EMA 10"),("EMA_20","EMA 20"),("EMA_50","EMA 50")]:
        if col in df_proc.columns:
            v=float(last[col]); a=action_from_ma(close_price,v)
            ma_items.append((label,v,a)); ma_actions.append(a)
    if not ma_items:
        ma_items.append(("No moving averages",np.nan,"N/A")); ma_actions.append("N/A")

    osc_counts = aggregate_counts(osc_actions)
    ma_counts  = aggregate_counts(ma_actions)
    combined_actions = [*osc_actions,*ma_actions]
    combined_counts  = aggregate_counts(combined_actions)

    def pick_dominant(counts):
        ordered=["Strong Buy","Buy","Neutral","Sell","Strong Sell"]
        best=max(ordered,key=lambda k:(counts.get(k,0),-ordered.index(k)))
        return "Neutral" if sum(counts.get(k,0) for k in counts if k!="N/A")==0 else best

    dominant_osc=pick_dominant(osc_counts); dominant_ma=pick_dominant(ma_counts)
    dominant_overall=pick_dominant(combined_counts)
    osc_val=ACTION_TO_VAL.get(dominant_osc,50); ma_val=ACTION_TO_VAL.get(dominant_ma,50)
    overall_val=ACTION_TO_VAL.get(dominant_overall,50)

    gcol1,gcol2,gcol3 = st.columns(3)
    with gcol1:
        st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
        fig_osc = make_gauge("Oscillators", osc_val,
            subtitle=f"Buy:{osc_counts['Buy']+osc_counts['Strong Buy']}  Neutral:{osc_counts['Neutral']}  Sell:{osc_counts['Sell']+osc_counts['Strong Sell']}")
        st.plotly_chart(fig_osc, width="stretch", config={'displayModeBar':False})
        st.markdown(f'<div class="gauge-label">Dominant: <b style="color:var(--gold-lt)">{dominant_osc}</b></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with gcol2:
        st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
        fig_sum = make_gauge("Summary", overall_val,
            subtitle=f"Buy:{combined_counts['Buy']+combined_counts['Strong Buy']}  Neutral:{combined_counts['Neutral']}  Sell:{combined_counts['Sell']+combined_counts['Strong Sell']}")
        st.plotly_chart(fig_sum, width="stretch", config={'displayModeBar':False})
        st.markdown(f'<div class="gauge-label">Dominant: <b style="color:var(--gold-lt)">{dominant_overall}</b></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with gcol3:
        st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
        fig_ma_ = make_gauge("Moving Averages", ma_val,
            subtitle=f"Buy:{ma_counts['Buy']+ma_counts['Strong Buy']}  Neutral:{ma_counts['Neutral']}  Sell:{ma_counts['Sell']+ma_counts['Strong Sell']}")
        st.plotly_chart(fig_ma_, width="stretch", config={'displayModeBar':False})
        st.markdown(f'<div class="gauge-label">Dominant: <b style="color:var(--gold-lt)">{dominant_ma}</b></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Tables
    st.markdown('<hr>', unsafe_allow_html=True)
    tcol1, tcol2 = st.columns([1.4, 1])
    with tcol1:
        st.markdown('<div class="section-label">⬡ &nbsp;Oscillators</div>', unsafe_allow_html=True)
        df_osc = pd.DataFrame(osc_items, columns=["Indicator","Value","Signal"])
        df_osc["Value"] = df_osc["Value"].apply(lambda v: f"{v:.4f}" if pd.notna(v) and isinstance(v,(float,int)) else v)
        st.dataframe(df_osc, width="stretch", hide_index=True)
    with tcol2:
        st.markdown('<div class="section-label">⬡ &nbsp;Moving Averages</div>', unsafe_allow_html=True)
        df_ma_df = pd.DataFrame(ma_items, columns=["MA","Value","Signal"])
        df_ma_df["Value"] = df_ma_df["Value"].apply(lambda v: f"{v:.4f}" if pd.notna(v) and isinstance(v,(float,int)) else v)
        st.dataframe(df_ma_df, width="stretch", hide_index=True)

    # ── TABS ───────────────────────────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    tab_overview, tab_charts, tab_renko, tab_data = st.tabs(
        ["⬡  Overview","⬡  Charts","⬡  Renko","⬡  Data"]
    )

    CHART_CONFIG = {
        'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False,
        'modeBarButtonsToAdd': ['pan2d','zoomIn2d','zoomOut2d','resetViews']
    }

    with tab_overview:
        st.markdown('<div class="section-label">⬡ &nbsp;Instrument Summary</div>', unsafe_allow_html=True)
        st.markdown(f"""
        | Field | Value |
        |---|---|
        | **Ticker** | `{ticker}` |
        | **Company** | {company_info['name']} |
        | **Sector** | {company_info['sector']} |
        | **Exchange** | {company_info['exchange']} |
        | **Period** | {period} |
        | **Interval** | {interval} |
        | **Rows (post-indicators)** | {len(df_proc):,} |
        | **Last Close** | `{last_close:,.2f}` |
        """)
        if company_info['summary']:
            with st.expander("⬡  Company Description"):
                st.write(company_info['summary'])

    with tab_charts:
        # Apex Main Price Engine (Restored Plotly Candlesticks - Stable)
        try:
            fig_price = plot_candlestick(df_proc)
            st.plotly_chart(fig_price, use_container_width=True, config=CHART_CONFIG)
        except Exception as e:
            st.error(f"Price Chart Error: {e}")

        # Modular Technical Indicators (Plotly Panels)
        try:
            st.plotly_chart(plot_volume(df_proc), use_container_width=True, config=CHART_CONFIG)
            st.plotly_chart(plot_rsi(df_proc), use_container_width=True, config=CHART_CONFIG)
            st.plotly_chart(plot_macd(df_proc), use_container_width=True, config=CHART_CONFIG)
        except Exception as e:
            st.error(f"Technical Indicator Error: {e}")

    with tab_renko:
        st.markdown('<div class="section-label">⬡ &nbsp;Renko Price Chart</div>', unsafe_allow_html=True)
        if renko_bricks and len(renko_bricks) > 0:
            try:
                fig_renko = plot_renko(renko_bricks, renko_brick_size)
                st.plotly_chart(fig_renko, width="stretch", config=CHART_CONFIG)
                col1,col2,col3,col4 = st.columns(4)
                with col1: st.metric("Total Bricks", renko_total_bricks)
                with col2: st.metric("Up Bricks ▲", renko_up_bricks)
                with col3: st.metric("Down Bricks ▼", renko_down_bricks)
                with col4: st.metric("Brick Size", f"{renko_brick_size:.2f}")
            except Exception as e:
                st.error(f"Renko chart error: {e}")
                with st.expander("Debug Info"):
                    st.write(f"Bricks: {len(renko_bricks)}")
                    if renko_bricks: st.write(f"First brick type: {type(renko_bricks[0])}")
        else:
            st.warning("No Renko bricks available for display.")

        with st.expander("⬡  What is Renko?"):
            st.markdown("""
**Renko Charts** strip away time and focus purely on price movement.

- **Green bricks** — price moved UP by one brick size  
- **Red bricks** — price moved DOWN by one brick size  
- Filters market noise · Clarifies trend direction · Reveals support/resistance
            """)

    with tab_data:
        st.markdown('<div class="section-label">⬡ &nbsp;Processed Indicator Data</div>', unsafe_allow_html=True)
        st.dataframe(df_proc, width="stretch", hide_index=True)
        with st.expander("⬡  Full column list"):
            st.write(list(df_proc.columns))

# ── IDLE STATE ─────────────────────────────────────────────────────
else:
    st.markdown("""
    <div style="text-align:center;padding:60px 0 20px;animation:fadeUp 0.6s ease both;">
      <div style="font-size:48px;margin-bottom:16px;opacity:0.3;">⬡</div>
      <div style="font-family:'DM Mono',monospace;font-size:13px;color:#4a5568;
                  letter-spacing:0.2em;text-transform:uppercase;">
        Enter a ticker above and click Analyze
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">⬡ &nbsp;Quick Pick</div>', unsafe_allow_html=True)
    examples = st.columns(5)
    for col, ticker_ex in zip(examples, ["AAPL","TSLA","MSFT","GOOGL","NVDA"]):
        with col:
            st.markdown('<div class="ticker-btn">', unsafe_allow_html=True)
            if st.button(ticker_ex, width="stretch"):
                st.session_state.ticker = ticker_ex
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
