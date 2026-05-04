import streamlit as st


# -------------------------------------------
# SIMPLE AUTH
# -------------------------------------------
def authenticate(username: str, password: str) -> bool:
    return username == "admin" and password == "admin123"


# -------------------------------------------
# LOGIN PAGE
# -------------------------------------------
def show_login():

    st.set_page_config(
        page_title="Trend-Based Halal Trading System",
        page_icon="⬡",
        layout="wide"
    )
    

    st.markdown("""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    /* ── ROOT VARIABLES ── */
    :root {
        --gold:    #c9a84c;
        --gold-lt: #e8c97a;
        --ink:     #080c12;
        --surface: #0d1320;
        --panel:   #111927;
        --border:  rgba(201,168,76,0.18);
        --muted:   #4a5568;
        --text:    #e2e8f0;
    }

    /* ── HIDE STREAMLIT CHROME ── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    section[data-testid="stSidebar"] { display: none; }

    /* ── FULL-SCREEN CANVAS ── */
    .stApp {
        background: var(--ink);
        font-family: 'Syne', sans-serif;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    /* ── ANIMATED GRID BACKGROUND ── */
    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background-image:
            linear-gradient(rgba(201,168,76,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(201,168,76,0.04) 1px, transparent 1px);
        background-size: 48px 48px;
        animation: gridDrift 25s linear infinite;
        pointer-events: none;
        z-index: 0;
    }

    @keyframes gridDrift {
        0%   { background-position: 0 0; }
        100% { background-position: 48px 48px; }
    }

    /* ── RADIAL GLOW ── */
    .stApp::after {
        content: '';
        position: fixed;
        top: -20%;
        left: 50%;
        transform: translateX(-50%);
        width: 700px;
        height: 700px;
        background: radial-gradient(circle, rgba(201,168,76,0.07) 0%, transparent 65%);
        pointer-events: none;
        z-index: 0;
        animation: pulse 6s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 0.6; transform: translateX(-50%) scale(1); }
        50%       { opacity: 1;   transform: translateX(-50%) scale(1.12); }
    }

    /* ── WRAPPER ── */
    .apex-wrap {
        position: relative;
        z-index: 10;
        width: 100%;
        max-width: 440px;
        margin: 0 auto;
        padding: 20px;
        animation: riseIn 0.8s cubic-bezier(0.16,1,0.3,1) both;
    }

    @keyframes riseIn {
        from { opacity: 0; transform: translateY(40px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* ── CARD ── */
    .apex-card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 48px 44px 40px;
        box-shadow:
            0 0 0 1px rgba(201,168,76,0.06),
            0 40px 80px rgba(0,0,0,0.7),
            inset 0 1px 0 rgba(255,255,255,0.04);
        position: relative;
        overflow: hidden;
    }

    /* ── CARD CORNER ACCENT ── */
    .apex-card::before {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 120px; height: 120px;
        background: conic-gradient(from 225deg at 100% 0%, rgba(201,168,76,0.15), transparent 60%);
        pointer-events: none;
    }

    /* ── TICKER TAPE ── */
    .ticker-wrap {
        overflow: hidden;
        border-bottom: 1px solid var(--border);
        margin: -48px -44px 40px;
        padding: 10px 0;
        background: rgba(201,168,76,0.04);
    }

    .ticker-inner {
        display: flex;
        gap: 48px;
        white-space: nowrap;
        animation: ticker 18s linear infinite;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--gold);
        letter-spacing: 0.05em;
    }

    @keyframes ticker {
        from { transform: translateX(0); }
        to   { transform: translateX(-50%); }
    }

    .tick-item { display: flex; align-items: center; gap: 6px; }
    .tick-up   { color: #4ade80; }
    .tick-dn   { color: #f87171; }

    /* ── LOGO MARK ── */
    .logo-mark {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 8px;
    }

    .hex-icon {
        width: 44px; height: 44px;
        background: linear-gradient(135deg, var(--gold) 0%, var(--gold-lt) 100%);
        clip-path: polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        box-shadow: 0 0 24px rgba(201,168,76,0.4);
        animation: hexGlow 3s ease-in-out infinite;
    }

    @keyframes hexGlow {
        0%, 100% { box-shadow: 0 0 20px rgba(201,168,76,0.35); }
        50%       { box-shadow: 0 0 40px rgba(201,168,76,0.65); }
    }

    .brand-name {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--text);
    }

    .brand-name span {
        background: linear-gradient(135deg, var(--gold) 0%, var(--gold-lt) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* ── HEADLINE ── */
    .headline {
        font-size: 13px;
        font-weight: 400;
        color: var(--muted);
        letter-spacing: 0.14em;
        text-transform: uppercase;
        font-family: 'DM Mono', monospace;
        margin-bottom: 36px;
        padding-bottom: 28px;
        border-bottom: 1px solid var(--border);
    }

    /* ── FIELD LABELS ── */
    .field-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .field-label::before {
        content: '';
        display: block;
        width: 6px; height: 6px;
        background: var(--gold);
        clip-path: polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%);
    }

    /* ── INPUT OVERRIDES ── */
    .stTextInput > div > div > input {
        background: var(--surface) !important;
        border: 1px solid rgba(201,168,76,0.2) !important;
        border-radius: 10px !important;
        color: var(--text) !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 14px !important;
        padding: 13px 16px !important;
        transition: border-color 0.25s, box-shadow 0.25s !important;
        letter-spacing: 0.04em;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 3px rgba(201,168,76,0.12), 0 0 20px rgba(201,168,76,0.08) !important;
        outline: none !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: rgba(74,85,104,0.8) !important;
        font-size: 13px;
    }

    /* remove streamlit default label */
    .stTextInput label { display: none !important; }

    /* ── SUBMIT BUTTON ── */
    .stButton > button {
        width: 100% !important;
        height: 52px !important;
        border-radius: 12px !important;
        background: linear-gradient(135deg, #b8922f 0%, var(--gold-lt) 50%, #b8922f 100%) !important;
        background-size: 200% 100% !important;
        color: var(--ink) !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        border: none !important;
        transition: background-position 0.4s ease, transform 0.2s, box-shadow 0.2s !important;
        box-shadow: 0 4px 24px rgba(201,168,76,0.25) !important;
        margin-top: 8px;
    }

    .stButton > button:hover {
        background-position: 100% 0 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 32px rgba(201,168,76,0.45) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── STATS ROW ── */
    .stats-row {
        display: flex;
        justify-content: space-between;
        margin-top: 32px;
        padding-top: 24px;
        border-top: 1px solid var(--border);
        gap: 12px;
    }

    .stat {
        text-align: center;
        flex: 1;
    }

    .stat-val {
        font-family: 'DM Mono', monospace;
        font-size: 16px;
        font-weight: 500;
        color: var(--gold-lt);
        letter-spacing: -0.02em;
    }

    .stat-lbl {
        font-size: 10px;
        color: var(--muted);
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-top: 3px;
    }

    .stat-sep {
        width: 1px;
        background: var(--border);
        align-self: stretch;
    }

    /* ── ALERTS ── */
    .stAlert {
        border-radius: 10px !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 13px !important;
    }

    /* ── SECURITY BADGE ── */
    .sec-badge {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        margin-top: 20px;
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: #374151;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .sec-dot {
        width: 5px; height: 5px;
        border-radius: 50%;
        background: #22c55e;
        box-shadow: 0 0 6px #22c55e;
        animation: blink 2s ease-in-out infinite;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.3; }
    }

    /* ── FORM FIELD SPACING ── */
    .stForm > div { gap: 0 !important; }
    div[data-testid="stFormSubmitButton"] { margin-top: 20px; }

    </style>
    """, unsafe_allow_html=True)

    # ── COLUMN CENTERING ──
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown('<div class="apex-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="apex-card">', unsafe_allow_html=True)

        # ── TICKER TAPE ──
        ticks = "SPY +0.84%&nbsp;&nbsp;|&nbsp;&nbsp;QQQ +1.12%&nbsp;&nbsp;|&nbsp;&nbsp;NVDA +3.47%&nbsp;&nbsp;|&nbsp;&nbsp;TSLA -1.23%&nbsp;&nbsp;|&nbsp;&nbsp;AAPL +0.56%&nbsp;&nbsp;|&nbsp;&nbsp;BTC +2.89%&nbsp;&nbsp;|&nbsp;&nbsp;ETH +1.74%&nbsp;&nbsp;|&nbsp;&nbsp;GLD -0.31%&nbsp;&nbsp;|&nbsp;&nbsp;"
        st.markdown(f"""
        <div class="ticker-wrap">
          <div class="ticker-inner">
            <span>{ticks}{ticks}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── LOGO + HEADLINE ──
        st.markdown("""
        <div class="logo-mark">
          <div class="hex-icon">⬡</div>
          <div class="brand-name">APE<span>X</span></div>
        </div>
        <div class="headline">AI-Powered Trend Intelligence Platform</div>
        """, unsafe_allow_html=True)

        # ── LOGIN FORM ──
        with st.form("login_form"):

            st.markdown('<div class="field-label">Username</div>', unsafe_allow_html=True)
            username = st.text_input("u", placeholder="trader_handle", label_visibility="collapsed")

            st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

            st.markdown('<div class="field-label">Password</div>', unsafe_allow_html=True)
            password = st.text_input("p", type="password", placeholder="••••••••••••", label_visibility="collapsed")

            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

            submitted = st.form_submit_button("ACCESS PLATFORM →")

            if submitted:
                if authenticate(username, password):
                    st.session_state["authenticated"] = True
                    st.success("✓ Authentication successful — loading markets…")
                    st.rerun()
                else:
                    st.error("⚠ Access denied. Invalid credentials.")

        # ── STATS ROW ──
        st.markdown("""
        <div class="stats-row">
          <div class="stat">
            <div class="stat-val">$2.4B</div>
            <div class="stat-lbl">Volume Tracked</div>
          </div>
          <div class="stat-sep"></div>
          <div class="stat">
            <div class="stat-val">14ms</div>
            <div class="stat-lbl">Signal Latency</div>
          </div>
          <div class="stat-sep"></div>
          <div class="stat">
            <div class="stat-val">99.97%</div>
            <div class="stat-lbl">Uptime</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── SECURITY BADGE ──
        st.markdown("""
        <div class="sec-badge">
          <div class="sec-dot"></div>
          256-bit encrypted &nbsp;·&nbsp; SOC 2 certified &nbsp;·&nbsp; Zero-log policy
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # apex-card
        st.markdown('</div>', unsafe_allow_html=True)  # apex-wrap


# -------------------------------------------
# DASHBOARD (placeholder)
# -------------------------------------------
def show_dashboard():
    st.title("📈 Dashboard")
    st.write("Welcome, trader.")
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()


# -------------------------------------------
# MAIN
# -------------------------------------------
def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        show_dashboard()
    else:
        show_login()


if __name__ == "__main__":
    main()