import os
import streamlit as st

def load_css(file_name="styles.css"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, "assets", file_name)
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Error: Could not find CSS file at {css_path}")

def render_decision_banner(status: str, trend: str, ml_pred: int):
    """Renders a high-impact decision banner based on combined signals."""
    
    # 1. Determine Logic
    is_halal = status == "COMPLIANT"
    is_non_halal = status == "NON_COMPLIANT"
    is_bullish = (trend == "UPTREND") and (ml_pred == 1)
    
    if is_non_halal:
        color = "#ef4444" # Red
        title = "❌ AVOID – NON-HALAL"
        subtitle = "Equity fails Shariah financial or business criteria."
    elif not is_halal: # INSUFFICIENT or ERROR
        color = "#f59e0b" # Amber
        title = "⚠️ WAIT – INCOMPLETE DATA"
        subtitle = "Missing critical metrics to confirm compliance."
    elif is_bullish:
        color = "#10b981" # Green
        title = "🚀 HALAL BUY"
        subtitle = "Compliant stock with strong bullish technical alignment."
    elif trend == "DOWNTREND":
        color = "#3b82f6" # Blue
        title = "◆ VOID – BEARISH TREND"
        subtitle = "Stock is Halal but current market structure is bearish."
    else:
        color = "#6b7280" # Gray
        title = "⬡ WATCHLIST"
        subtitle = "Stock is Halal; waiting for clearer entry signals."

    st.markdown(f"""
    <div style="
        background: linear-gradient(90deg, {color}22 0%, transparent 100%);
        border-left: 5px solid {color};
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 25px;
        border: 1px solid {color}44;
    ">
        <div style="color: {color}; font-size: 24px; font-weight: 800; letter-spacing: -0.02em;">{title}</div>
        <div style="color: #94a3b8; font-family: var(--mono); font-size: 13px; margin-top: 4px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_halal_scorecard(halal_data: dict):
    """Renders a detailed visual scorecard for Halal metrics."""
    status = halal_data.get("status", "UNKNOWN")
    
    colors = {
        "COMPLIANT": "#10b981",
        "NON_COMPLIANT": "#ef4444",
        "INSUFFICIENT_DATA": "#f59e0b",
        "ERROR": "#6b7280"
    }
    color = colors.get(status, "#6b7280")
    
    st.markdown(f"""
    <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="font-family: var(--mono); font-size: 12px; color: var(--gold); text-transform: uppercase; letter-spacing: 0.1em;">Halal Compliance Audit</div>
            <div style="background: {color}22; color: {color}; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; border: 1px solid {color}44;">{status}</div>
        </div>
    """, unsafe_allow_html=True)
    
    ratios = halal_data.get("ratios", {})
    render_ratio_bar("Debt Ratio", ratios.get("debt_ratio"), 0.33)
    render_ratio_bar("Interest Ratio", ratios.get("interest_ratio"), 0.05)
    render_ratio_bar("Liquidity Ratio", ratios.get("liquidity_ratio"), 0.50)
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_ratio_bar(label, value, threshold):
    """Renders a visual progress bar for a financial ratio."""
    if value is None:
        val_str = "N/A"
        percent = 0
        color = "#4b5563"
    else:
        val_str = f"{value:.2%}"
        percent = min(int((value / (threshold * 1.5)) * 100), 100)
        color = "#10b981" if value < threshold else "#ef4444"
        
    st.markdown(f"""
    <div style="margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; font-family: var(--mono); font-size: 11px; margin-bottom: 6px;">
            <span style="color: #94a3b8;">{label}</span>
            <span style="color: {color}; font-weight: 600;">{val_str} <span style="color: #4b5563; font-weight: 400;">/ {threshold:.0%} limit</span></span>
        </div>
        <div style="background: #1e293b; height: 6px; border-radius: 3px; overflow: hidden;">
            <div style="background: {color}; width: {percent}%; height: 100%; transition: width 0.6s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
