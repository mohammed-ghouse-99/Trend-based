import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import json

# ── APEX TRADING DESIGN SYSTEM ────────────────────────────────────
APEX_THEME = {
    "background": "#060910",
    "surface": "#0f1623",
    "bull": "#26a69a",
    "bear": "#ef5350",
    "grid": "rgba(255, 255, 255, 0.05)",
    "axis": "#c9a84c",
    "gold": "#c9a84c",
    "text": "#e2e8f0",
    "muted": "#6b7280",
    "gold_dim": "rgba(201, 168, 76, 0.12)",
    "font_family": "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"
}

def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    return df

def _apply_apex_style(fig: go.Figure, title: str = None, height: int = 400):
    fig.update_layout(
        title=dict(text=f"&nbsp; {title.upper()}" if title else "", font=dict(family="Syne, sans-serif", size=12, color=APEX_THEME["gold"]), x=0, y=0.98),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=APEX_THEME["background"],
        font=dict(family=APEX_THEME.get("font_family", "monospace"), color=APEX_THEME["text"], size=11),
        margin=dict(l=10, r=10, t=40, b=30), height=height, hovermode="x unified", dragmode="pan", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=APEX_THEME["muted"])),
        xaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor", showline=True, showgrid=True, gridcolor=APEX_THEME["grid"], linecolor=APEX_THEME["grid"], gridwidth=1, griddash="dot", tickfont=dict(color=APEX_THEME["muted"]), zeroline=False),
        yaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor", showline=True, showgrid=True, gridcolor=APEX_THEME["grid"], linecolor=APEX_THEME["grid"], gridwidth=1, griddash="dot", tickfont=dict(color=APEX_THEME["muted"]), zeroline=False, side="right")
    )
    fig.update_traces(hoverlabel=dict(bgcolor=APEX_THEME["surface"], font_size=12, font_family=APEX_THEME.get("font_family", "monospace")))
    return fig

# ── APEX MAIN PRICE ENGINE (STABLE PLOTLY) ────────────────────────
def plot_candlestick(df: pd.DataFrame) -> go.Figure:
    """Stable, high-fidelity Plotly Candlestick chart with Area/Candle Dual-Trace."""
    df = _ensure_datetime_index(df)
    fig = go.Figure()

    # Main Candles
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Candles",
        increasing_line_color=APEX_THEME["bull"],
        decreasing_line_color=APEX_THEME["bear"],
        visible=True
    ))

    # Area Overlay (Smooth Snapshot)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"], name="Area View",
        mode="lines", fill="tozeroy",
        fillcolor=APEX_THEME["gold_dim"],
        line=dict(color=APEX_THEME["gold"], width=2, shape="spline"),
        visible="legendonly"
    ))

    # Technicals
    colors = {"SMA_20": "#3b82f6", "SMA_50": "#f59e0b", "SMA_200": "#ec4899"}
    for sma, color in colors.items():
        if sma in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[sma], name=sma, line=dict(color=color, width=1.5), opacity=0.8))

    fig = _apply_apex_style(fig, "Apex Price Engine", height=600)
    fig.update_layout(xaxis_rangeslider_visible=False)
    return fig

# ── MODULAR TECHNICAL PANELS (PLOTLY) ─────────────────────────────
def plot_volume(df: pd.DataFrame) -> go.Figure:
    df = _ensure_datetime_index(df)
    clrs = [APEX_THEME["bull"] if c >= o else APEX_THEME["bear"] for o, c in zip(df["Open"], df["Close"])]
    fig = go.Figure(data=[go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=clrs, opacity=0.7)])
    return _apply_apex_style(fig, "Trading Volume Flow", height=240)

def plot_rsi(df: pd.DataFrame) -> go.Figure:
    df = _ensure_datetime_index(df)
    if "RSI_14" not in df.columns: return go.Figure()
    fig = go.Figure(go.Scatter(x=df.index, y=df["RSI_14"], name="RSI", line=dict(width=1.5, color=APEX_THEME["axis"])))
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(201,168,76,0.05)", opacity=0.3, line_width=0)
    return _apply_apex_style(fig, "Relative Strength Index", height=240)

def plot_macd(df: pd.DataFrame) -> go.Figure:
    df = _ensure_datetime_index(df)
    fig = go.Figure()
    if all(c in df.columns for c in ["MACD", "MACD_SIGNAL", "MACD_HIST"]):
        clrs = [APEX_THEME["bull"] if v >= 0 else APEX_THEME["bear"] for v in df["MACD_HIST"]]
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_HIST"], name="Hist", marker_color=clrs, opacity=0.4))
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(width=1.2, color="#3b82f6")))
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_SIGNAL"], name="Sig", line=dict(width=1.2, color="#f59e0b")))
    return _apply_apex_style(fig, "MACD Momentum Sync", height=240)

def plot_renko(bricks: list, brick_size: float) -> go.Figure:
    if not bricks: return go.Figure()
    fig = go.Figure()
    for b in bricks:
        if hasattr(b, 'to_dict'): b = b.to_dict()
        dir = b.get('direction', '').upper(); ts = b.get('timestamp'); pr = float(b.get('price', 0))
        clr = APEX_THEME["bull"] if dir == "UP" else APEX_THEME["bear"]
        y0, y1 = (pr - brick_size, pr) if dir == "UP" else (pr, pr + brick_size)
        fig.add_trace(go.Scatter(x=[ts, ts], y=[y0, y1], mode='lines', line=dict(color=clr, width=10), showlegend=False))
    return _apply_apex_style(fig, "Renko Market Structure", height=600)

# ── LEGACY & STUBS ────────────────────────────────────────────────
def render_price_chart(df: pd.DataFrame) -> str: return ""
def render_apex_terminal(df): return ""
def plot_integrated_terminal(df): return go.Figure()