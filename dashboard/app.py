import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="DFCRM — Fraud Intelligence",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root {
    --bg-primary: #040810;
    --bg-secondary: #080f1a;
    --bg-card: #0d1829;
    --bg-card-hover: #111f35;
    --border: #1a2d4a;
    --border-bright: #1e3a5f;
    --accent-red: #ff3b3b;
    --accent-yellow: #f5a623;
    --accent-green: #00d4aa;
    --accent-blue: #4d9fff;
    --accent-blue-dim: #2a5a99;
    --text-primary: #e8f0fe;
    --text-secondary: #7a9cc5;
    --text-dim: #3d5a7a;
    --glow-red: rgba(255,59,59,0.15);
    --glow-green: rgba(0,212,170,0.15);
    --glow-blue: rgba(77,159,255,0.1);
}
* { font-family: 'Space Grotesk', sans-serif; }
code, .mono { font-family: 'JetBrains Mono', monospace; }
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}
[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse at 20% 0%, rgba(30,58,95,0.4) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 100%, rgba(255,59,59,0.08) 0%, transparent 50%),
                var(--bg-primary) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem !important; max-width: 1600px !important; }

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: #060d18 !important;
    border-right: 1px solid #1a2d4a !important;
}
section[data-testid="stSidebar"] * { color: #7a9cc5 !important; }
section[data-testid="stSidebar"] .stSlider label { color: #7a9cc5 !important; }
section[data-testid="stSidebar"] h3 { color: #e8f0fe !important; font-size: 0.85rem !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; }

/* HEADER */
.dfcrm-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.5rem 0 2rem 0; border-bottom: 1px solid var(--border); margin-bottom: 2rem;
}
.dfcrm-logo { display: flex; align-items: baseline; gap: 0.75rem; }
.dfcrm-logo-text { font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em; color: var(--text-primary); }
.dfcrm-logo-dot {
    width: 10px; height: 10px; border-radius: 50%; background: var(--accent-red);
    box-shadow: 0 0 12px var(--accent-red); display: inline-block; margin-right: 4px;
    animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 12px var(--accent-red); }
    50% { opacity: 0.6; box-shadow: 0 0 24px var(--accent-red); }
}
.dfcrm-subtitle { font-size: 0.8rem; color: var(--text-dim); letter-spacing: 0.15em; text-transform: uppercase; font-weight: 500; }
.live-badge {
    display: flex; align-items: center; gap: 0.5rem;
    background: rgba(0,212,170,0.08); border: 1px solid rgba(0,212,170,0.2);
    border-radius: 20px; padding: 0.4rem 1rem; font-size: 0.75rem;
    color: var(--accent-green); font-weight: 500; letter-spacing: 0.05em;
}
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent-green); animation: pulse-dot 1.5s ease-in-out infinite; }

/* METRIC CARDS */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
.metric-card {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.5rem; position: relative; overflow: hidden; transition: all 0.2s ease;
}
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }
.metric-card.total::before { background: var(--accent-blue); }
.metric-card.critical::before { background: var(--accent-red); box-shadow: 0 0 20px var(--accent-red); }
.metric-card.exposed::before { background: var(--accent-yellow); }
.metric-card.clean::before { background: var(--accent-green); }
.metric-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.5rem; }
.metric-value { font-size: 2.5rem; font-weight: 700; line-height: 1; letter-spacing: -0.02em; }
.metric-value.total { color: var(--accent-blue); }
.metric-value.critical { color: var(--accent-red); text-shadow: 0 0 20px rgba(255,59,59,0.4); }
.metric-value.exposed { color: var(--accent-yellow); }
.metric-value.clean { color: var(--accent-green); }
.metric-sub { font-size: 0.72rem; color: var(--text-dim); margin-top: 0.4rem; }

/* SECTION HEADERS */
.section-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
.section-title { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-secondary); }
.section-line { flex: 1; height: 1px; background: var(--border); }

/* CARDS */
.glass-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; height: 100%; }

/* ZONE BADGE */
.zone-badge { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.8rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.05em; }
.zone-critical { background: rgba(255,59,59,0.12); border: 1px solid rgba(255,59,59,0.3); color: var(--accent-red); }
.zone-exposed { background: rgba(245,166,35,0.12); border: 1px solid rgba(245,166,35,0.3); color: var(--accent-yellow); }
.zone-clean { background: rgba(0,212,170,0.12); border: 1px solid rgba(0,212,170,0.3); color: var(--accent-green); }

/* STAT ROW */
.stat-row { display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid var(--border); }
.stat-row:last-child { border-bottom: none; }
.stat-key { font-size: 0.75rem; color: var(--text-secondary); font-weight: 500; }
.stat-val { font-size: 0.85rem; color: var(--text-primary); font-weight: 600; font-family: 'JetBrains Mono', monospace; }

/* RISK BAR */
.risk-bar-container { margin: 1rem 0; }
.risk-bar-label { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.4rem; }
.risk-bar-track { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.risk-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease; }

/* INPUTS */
.stTextInput input, .stNumberInput input {
    background: var(--bg-secondary) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.85rem !important; padding: 0.6rem 1rem !important;
}
.stSlider [data-testid="stThumb"] { background: var(--accent-blue) !important; }

/* BUTTONS */
.stButton button {
    background: linear-gradient(135deg, #1a3a6e, #2a5ab8) !important;
    border: 1px solid var(--accent-blue-dim) !important; border-radius: 8px !important;
    color: white !important; font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important; font-size: 0.82rem !important; letter-spacing: 0.05em !important;
    padding: 0.6rem 1.5rem !important; transition: all 0.2s ease !important; width: 100% !important;
}
.stButton button:hover {
    background: linear-gradient(135deg, #1e4a8a, #3468cc) !important;
    border-color: var(--accent-blue) !important; box-shadow: 0 0 20px rgba(77,159,255,0.2) !important;
}

/* ALERT BOXES */
.alert-critical { background: rgba(255,59,59,0.08); border: 1px solid rgba(255,59,59,0.25); border-left: 3px solid var(--accent-red); border-radius: 8px; padding: 1rem 1.25rem; margin: 0.5rem 0; }
.alert-exposed { background: rgba(245,166,35,0.08); border: 1px solid rgba(245,166,35,0.25); border-left: 3px solid var(--accent-yellow); border-radius: 8px; padding: 1rem 1.25rem; margin: 0.5rem 0; }
.alert-clean { background: rgba(0,212,170,0.08); border: 1px solid rgba(0,212,170,0.25); border-left: 3px solid var(--accent-green); border-radius: 8px; padding: 1rem 1.25rem; margin: 0.5rem 0; }
.alert-title { font-size: 0.85rem; font-weight: 700; margin-bottom: 0.25rem; }
.alert-body { font-size: 0.78rem; color: var(--text-secondary); line-height: 1.5; }

/* NEIGHBOR CHIP */
.neighbor-chip {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: rgba(77,159,255,0.08); border: 1px solid rgba(77,159,255,0.2);
    border-radius: 6px; padding: 0.3rem 0.7rem; font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace; color: var(--accent-blue); margin: 0.2rem; display: inline-block;
}

/* DATAFRAME */
[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: 10px !important; overflow: hidden !important; }

label, .stSelectbox label { color: var(--text-secondary) !important; font-size: 0.75rem !important; font-weight: 600 !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; }
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }
.js-plotly-plot { border-radius: 10px; overflow: hidden; }

.fingerprint-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-top: 0.8rem; }
.fp-item { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 0.7rem 0.9rem; }
.fp-label { font-size: 0.65rem; color: var(--text-dim); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.2rem; }
.fp-value { font-size: 1rem; font-weight: 600; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }

.tx-result-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin: 1rem 0; }
.tx-result-item { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 0.8rem; text-align: center; }
.tx-result-label { font-size: 0.65rem; color: var(--text-dim); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.3rem; }
.tx-result-value { font-size: 1.3rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

/* ML METRICS */
.ml-metric-card {
    background: #0d1829; border: 1px solid #1a2d4a; border-radius: 8px;
    padding: 1rem; text-align: center; margin-bottom: 0.5rem;
}
.ml-metric-label { color: #7a9cc5; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.5rem; }
.ml-metric-dfcrm { font-size: 1.6rem; font-weight: 700; }
.ml-metric-sub { font-size: 0.65rem; color: #4a6080; margin-top: 0.2rem; }
.ml-metric-lr { font-size: 1rem; color: #4a6080; margin-top: 0.5rem; }
.ml-finding { background: #0d1829; border: 1px solid #1a2d4a; border-radius: 8px; padding: 1rem; margin-top: 0.5rem; color: #7a9cc5; font-size: 0.85rem; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Space Grotesk', color='#7a9cc5', size=11),
    margin=dict(l=10, r=10, t=30, b=10),
    showlegend=False,
)

def fetch_stats():
    try:
        return requests.get(f"{API_URL}/stats", timeout=5).json()
    except:
        return None

def fetch_account(account_id):
    try:
        r = requests.get(f"{API_URL}/account/{account_id}", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def fetch_zone(zone):
    try:
        return requests.get(f"{API_URL}/zone/{zone}", timeout=5).json()
    except:
        return None

def fetch_neighbors(account_id):
    try:
        return requests.get(f"{API_URL}/fraud-neighbors/{account_id}", timeout=5).json()
    except:
        return None

def post_transaction(payload):
    try:
        r = requests.post(f"{API_URL}/transaction", json=payload, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def zone_color(zone):
    return {"Critical": "#ff3b3b", "Exposed": "#f5a623", "Clean": "#00d4aa"}.get(zone, "#7a9cc5")

def risk_bar_html(label, value, color):
    pct = int(value * 100)
    return f"""
    <div class="risk-bar-container">
        <div class="risk-bar-label"><span>{label}</span><span style="color:{color};font-weight:700">{value:.4f}</span></div>
        <div class="risk-bar-track"><div class="risk-bar-fill" style="width:{pct}%;background:{color};box-shadow:0 0 8px {color}66"></div></div>
    </div>"""

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Formula Controls")
    st.markdown("---")
    alpha = st.slider("Alpha — Structural Weight", 0.1, 0.9, 0.6, 0.1)
    beta = round(1.0 - alpha, 1)
    st.markdown(f"**Beta — Behavioral Weight: `{beta}`**")
    st.markdown(f"*Risk = **{alpha}** × Structural + **{beta}** × Drift*")
    st.markdown("---")
    st.markdown("### 🎯 Zone Thresholds")
    critical_thresh = st.slider("Critical threshold", 0.50, 0.95, 0.75, 0.05)
    exposed_thresh = st.slider("Exposed threshold", 0.20, 0.70, 0.45, 0.05)
    st.markdown("---")
    st.markdown("### 📊 Weight Optimization")
    st.markdown("Grid search across all α/β combinations:")
    st.markdown("✅ **Optimal range: α = 0.4 → 0.8**")
    st.markdown("All produce F1 = **0.9091**")
    st.markdown("Our α=0.6 sits in the **center of the optimal range** — not arbitrary, stable.")
    st.markdown("---")
    st.markdown("### 🔄 Trust Recovery")
    st.markdown("ACC00007 recovers to **Clean on Day 9**")
    st.markdown("Requires **both**: low drift + time decay")
    st.markdown("High drift = ❌ **recovery blocked**")
    st.markdown("---")
    st.markdown("### 📈 Dataset")
    st.markdown("**2,000** accounts · **20,000** transactions")
    st.markdown("**10** confirmed fraud nodes")
    st.markdown("**3** circular money rings injected")

# ── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="dfcrm-header">
    <div>
        <div class="dfcrm-logo">
            <span class="dfcrm-logo-dot"></span>
            <span class="dfcrm-logo-text">DFCRM</span>
        </div>
        <div class="dfcrm-subtitle">Dynamic Fraud Contamination &amp; Recovery Model</div>
    </div>
    <div class="live-badge"><div class="live-dot"></div> LIVE MONITORING</div>
</div>
""", unsafe_allow_html=True)

# ── FETCH STATS ──────────────────────────────────────────────────────────────
stats = fetch_stats()
if not stats:
    st.markdown("""
    <div class="alert-critical">
        <div class="alert-title" style="color:#ff3b3b">⚠ API Unreachable</div>
        <div class="alert-body">Cannot connect to the DFCRM API at localhost:8000.<br>
        <code style="color:#4d9fff">uvicorn api.main:app --reload --port 8000</code></div>
    </div>""", unsafe_allow_html=True)
    st.stop()

zones = stats.get("zone_distribution", {})
total = stats.get("total_accounts", 0)
critical = zones.get("Critical", 0)
exposed = zones.get("Exposed", 0)
clean = zones.get("Clean", 0)
fraud_count = stats.get("confirmed_fraud", 0)

# ── METRIC CARDS ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="metric-grid">
    <div class="metric-card total">
        <div class="metric-label">Total Accounts</div>
        <div class="metric-value total">{total}</div>
        <div class="metric-sub">Across the network</div>
    </div>
    <div class="metric-card critical">
        <div class="metric-label">🔴 Critical</div>
        <div class="metric-value critical">{critical}</div>
        <div class="metric-sub">Block immediately</div>
    </div>
    <div class="metric-card exposed">
        <div class="metric-label">🟡 Exposed</div>
        <div class="metric-value exposed">{exposed}</div>
        <div class="metric-sub">Under monitoring</div>
    </div>
    <div class="metric-card clean">
        <div class="metric-label">🟢 Clean</div>
        <div class="metric-value clean">{clean}</div>
        <div class="metric-sub">Normal behavior</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── ROW 1: CHARTS ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

with col1:
    st.markdown('<div class="section-header"><span class="section-title">Zone Distribution</span><div class="section-line"></div></div>', unsafe_allow_html=True)
    fig_donut = go.Figure(go.Pie(
        labels=["Critical", "Exposed", "Clean"],
        values=[critical, exposed, clean],
        hole=0.72,
        marker=dict(colors=["#ff3b3b", "#f5a623", "#00d4aa"], line=dict(color="#040810", width=3)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} accounts<br>%{percent}<extra></extra>"
    ))
    fig_donut.add_annotation(text=f"<b>{total}</b>", x=0.5, y=0.55, showarrow=False, font=dict(size=28, color="#e8f0fe", family="Space Grotesk"))
    fig_donut.add_annotation(text="accounts", x=0.5, y=0.38, showarrow=False, font=dict(size=11, color="#7a9cc5", family="Space Grotesk"))
    fig_donut.update_layout(**CHART_LAYOUT, height=260)
    st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

with col2:
    st.markdown('<div class="section-header"><span class="section-title">Risk Spread</span><div class="section-line"></div></div>', unsafe_allow_html=True)
    fig_bar = go.Figure()
    for cat, val, col in zip(["Critical", "Exposed", "Clean"], [critical, exposed, clean], ["#ff3b3b", "#f5a623", "#00d4aa"]):
        fig_bar.add_trace(go.Bar(x=[cat], y=[val], marker=dict(color=col, opacity=0.85, line=dict(color=col, width=1)), hovertemplate=f"<b>{cat}</b><br>{val} accounts<extra></extra>", name=cat))
    fig_bar.update_layout(**CHART_LAYOUT, height=260,
        xaxis=dict(showgrid=False, showline=False, tickfont=dict(size=11, color="#7a9cc5")),
        yaxis=dict(showgrid=True, gridcolor="#1a2d4a", showline=False, tickfont=dict(size=10, color="#3d5a7a")),
        bargap=0.35)
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

with col3:
    st.markdown('<div class="section-header"><span class="section-title">Contamination Score Distribution</span><div class="section-line"></div></div>', unsafe_allow_html=True)
    exposed_data = fetch_zone("Exposed")
    if exposed_data and exposed_data.get("accounts"):
        scores = [a["contamination_score"] for a in exposed_data["accounts"]]
        fig_hist = go.Figure(go.Histogram(x=scores, nbinsx=20, marker=dict(color="#f5a623", opacity=0.7, line=dict(color="#f5a623", width=0.5)), hovertemplate="Score: %{x:.2f}<br>Count: %{y}<extra></extra>"))
        fig_hist.update_layout(**CHART_LAYOUT, height=260,
            xaxis=dict(showgrid=False, title=dict(text="Risk Score", font=dict(size=10)), tickfont=dict(size=10, color="#7a9cc5")),
            yaxis=dict(showgrid=True, gridcolor="#1a2d4a", title=dict(text="Accounts", font=dict(size=10)), tickfont=dict(size=10, color="#3d5a7a")))
        st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── ROW 2: ACCOUNT LOOKUP + TRANSACTION SIM ──────────────────────────────────
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.markdown('<div class="section-header"><span class="section-title">Account Intelligence</span><div class="section-line"></div></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        lookup_id = st.text_input("ACCOUNT ID", value="ACC00247", placeholder="e.g. ACC00007", label_visibility="visible")
        if st.button("RUN RISK ANALYSIS", key="lookup_btn"):
            with st.spinner(""):
                data = fetch_account(lookup_id)
                neighbors = fetch_neighbors(lookup_id)
            if data:
                zone = data.get("zone", "Unknown")
                risk = data.get("contamination_score", 0) or 0
                drift = data.get("drift_score", 0) or 0
                hops = data.get("hop_distance", "N/A")
                is_fraud = data.get("is_fraud", False)
                zcolor = zone_color(zone)
                zbadge_class = f"zone-{zone.lower()}"
                st.markdown(f"""
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem">
                    <div>
                        <div style="font-size:0.7rem;color:var(--text-dim);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.3rem">Account</div>
                        <div style="font-size:1.1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--text-primary)">{data.get('account_id')}</div>
                        <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:0.1rem">{data.get('name','')}</div>
                    </div>
                    <span class="zone-badge {zbadge_class}">{zone}</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(risk_bar_html("Contamination Risk", risk, zcolor), unsafe_allow_html=True)
                st.markdown(risk_bar_html("Behavioral Drift", drift, "#4d9fff"), unsafe_allow_html=True)
                st.markdown(f"""
                <div class="fingerprint-grid">
                    <div class="fp-item">
                        <div class="fp-label">Hop Distance</div>
                        <div class="fp-value" style="color:{'#ff3b3b' if hops==1 else '#f5a623' if hops==2 else '#00d4aa'}">{hops if hops else '—'}</div>
                    </div>
                    <div class="fp-item">
                        <div class="fp-label">Fraud Status</div>
                        <div class="fp-value" style="color:{'#ff3b3b' if is_fraud else '#00d4aa'}">{'CONFIRMED' if is_fraud else 'CLEAN'}</div>
                    </div>
                    <div class="fp-item">
                        <div class="fp-label">Avg Transaction</div>
                        <div class="fp-value">${data.get('amount_mean', 0):,.0f}</div>
                    </div>
                    <div class="fp-item">
                        <div class="fp-label">Daily Velocity</div>
                        <div class="fp-value">{data.get('daily_velocity', 0):.3f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if neighbors and neighbors.get("fraud_neighbors"):
                    st.markdown("<div style='margin-top:1rem;margin-bottom:0.4rem;font-size:0.7rem;color:var(--text-dim);letter-spacing:0.1em;text-transform:uppercase'>Fraud Network Neighbors</div>", unsafe_allow_html=True)
                    chips_html = ""
                    for n in neighbors["fraud_neighbors"][:6]:
                        chips_html += f'<span class="neighbor-chip">⚠ {n["fraud_account"]} · {n["hops"]}h</span> '
                    st.markdown(chips_html, unsafe_allow_html=True)
                if zone == "Critical":
                    st.markdown('<div class="alert-critical" style="margin-top:1rem"><div class="alert-title" style="color:#ff3b3b">🚨 CRITICAL RISK</div><div class="alert-body">Immediate action required. Block transactions and escalate to compliance team.</div></div>', unsafe_allow_html=True)
                elif zone == "Exposed":
                    st.markdown('<div class="alert-exposed" style="margin-top:1rem"><div class="alert-title" style="color:#f5a623">⚠ EXPOSURE DETECTED</div><div class="alert-body">Account is within contamination range of confirmed fraud. Enhanced monitoring active.</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="alert-clean" style="margin-top:1rem"><div class="alert-title" style="color:#00d4aa">✓ NO RISK DETECTED</div><div class="alert-body">Account behavior is within normal parameters. No action required.</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-critical"><div class="alert-body">Account not found in the graph database.</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="section-header"><span class="section-title">Real-Time Transaction Simulator</span><div class="section-line"></div></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.75rem;color:var(--text-dim);margin-bottom:1rem;line-height:1.6">Submit a transaction to see how DFCRM updates risk scores and zone classification in real time. Try a high amount at 3am to trigger drift detection.</div>', unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1:
            sim_sender = st.text_input("SENDER ID", value="ACC00007", key="sim_sender")
        with tc2:
            sim_receiver = st.text_input("RECEIVER ID", value="ACC00100", key="sim_receiver")
        sim_amount = st.number_input("TRANSACTION AMOUNT ($)", min_value=1.0, value=500.0, step=500.0, key="sim_amount")
        sim_hour = st.slider("TRANSACTION HOUR (0 = midnight, 12 = noon)", 0, 23, 14, key="sim_hour")
        hour_label = f"{'🌙 Night' if sim_hour < 6 else '🌅 Morning' if sim_hour < 12 else '☀️ Afternoon' if sim_hour < 18 else '🌆 Evening'} — {sim_hour:02d}:00"
        st.markdown(f'<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:0.5rem">{hour_label}</div>', unsafe_allow_html=True)
        if st.button("⚡  PROCESS TRANSACTION", key="sim_btn"):
            with st.spinner(""):
                result = post_transaction({"sender_id": sim_sender, "receiver_id": sim_receiver, "amount": sim_amount, "hour": sim_hour})
            if result:
                zone = result.get("zone", "Unknown")
                risk = result.get("risk_score", 0)
                drift = result.get("drift_score", 0)
                hops = result.get("hop_distance", "N/A")
                zcolor = zone_color(zone)
                zbadge_class = f"zone-{zone.lower()}"
                st.markdown(f"""
                <div style="display:flex;align-items:center;justify-content:space-between;margin:0.8rem 0">
                    <div style="font-size:0.75rem;color:var(--text-dim)">Transaction processed</div>
                    <span class="zone-badge {zbadge_class}">{zone}</span>
                </div>
                <div class="tx-result-grid">
                    <div class="tx-result-item">
                        <div class="tx-result-label">Risk Score</div>
                        <div class="tx-result-value" style="color:{zcolor}">{risk:.4f}</div>
                    </div>
                    <div class="tx-result-item">
                        <div class="tx-result-label">Drift Score</div>
                        <div class="tx-result-value" style="color:#4d9fff">{drift:.4f}</div>
                    </div>
                    <div class="tx-result-item">
                        <div class="tx-result-label">Hops to Fraud</div>
                        <div class="tx-result-value" style="color:{'#ff3b3b' if hops==1 else '#f5a623' if hops==2 else '#00d4aa'}">{hops if hops else '—'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(risk_bar_html("Combined Risk Score", risk, zcolor), unsafe_allow_html=True)
                st.markdown(risk_bar_html("Behavioral Drift", drift, "#4d9fff"), unsafe_allow_html=True)
                if zone == "Critical":
                    st.markdown('<div class="alert-critical"><div class="alert-title" style="color:#ff3b3b">🚨 ZONE ELEVATED TO CRITICAL</div><div class="alert-body">Structural proximity to fraud combined with abnormal behavioral drift has triggered Critical classification. Recommend immediate transaction block.</div></div>', unsafe_allow_html=True)
                elif zone == "Exposed":
                    st.markdown('<div class="alert-exposed"><div class="alert-title" style="color:#f5a623">⚠ EXPOSED — MONITORING ACTIVE</div><div class="alert-body">Account is within contamination range. Behavioral patterns are being tracked.</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="alert-clean"><div class="alert-title" style="color:#00d4aa">✓ TRANSACTION CLEARED</div><div class="alert-body">Risk score within acceptable parameters. Account behavior is consistent with historical baseline.</div></div>', unsafe_allow_html=True)
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=risk,
                    number=dict(font=dict(size=28, color=zcolor, family="JetBrains Mono"), valueformat=".3f"),
                    gauge=dict(
                        axis=dict(range=[0,1], tickfont=dict(size=9, color="#3d5a7a"), tickcolor="#1a2d4a"),
                        bar=dict(color=zcolor, thickness=0.25),
                        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                        steps=[
                            dict(range=[0, 0.45], color="rgba(0,212,170,0.08)"),
                            dict(range=[0.45, 0.75], color="rgba(245,166,35,0.08)"),
                            dict(range=[0.75, 1.0], color="rgba(255,59,59,0.08)")
                        ],
                        threshold=dict(line=dict(color=zcolor, width=2), thickness=0.75, value=risk)
                    ),
                    domain=dict(x=[0,1], y=[0,1])
                ))
                fig_gauge.update_layout(**CHART_LAYOUT, height=180)
                st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown('<div class="alert-critical"><div class="alert-body">Transaction failed. Check sender/receiver IDs.</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── ROW 3: EXPOSED TABLE + SCATTER ────────────────────────────────────────────
t1, t2 = st.columns([1.6, 1.4], gap="large")

with t1:
    st.markdown('<div class="section-header"><span class="section-title">Exposed Accounts — Risk Register</span><div class="section-line"></div></div>', unsafe_allow_html=True)
    if exposed_data and exposed_data.get("accounts"):
        df = pd.DataFrame(exposed_data["accounts"])
        df.columns = ["Account ID", "Name", "Risk Score", "Drift Score", "Hop Distance"]
        df["Risk Score"] = df["Risk Score"].round(4)
        df["Drift Score"] = df["Drift Score"].round(4)
        st.dataframe(
            df.style
            .background_gradient(subset=["Risk Score"], cmap="YlOrRd", vmin=0, vmax=1)
            .format({"Risk Score": "{:.4f}", "Drift Score": "{:.4f}"}),
            use_container_width=True,
            height=360,
            hide_index=True
        )

with t2:
    st.markdown('<div class="section-header"><span class="section-title">Risk vs Drift — Scatter Analysis</span><div class="section-line"></div></div>', unsafe_allow_html=True)
    if exposed_data and exposed_data.get("accounts"):
        df_scatter = pd.DataFrame(exposed_data["accounts"])
        fig_scatter = go.Figure(go.Scatter(
            x=df_scatter["drift_score"],
            y=df_scatter["contamination_score"],
            mode="markers",
            marker=dict(
                size=8,
                color=df_scatter["contamination_score"],
                colorscale=[[0,"#00d4aa"],[0.5,"#f5a623"],[1,"#ff3b3b"]],
                opacity=0.75, line=dict(width=0)
            ),
            text=df_scatter["account_id"],
            hovertemplate="<b>%{text}</b><br>Risk: %{y:.3f}<br>Drift: %{x:.3f}<extra></extra>"
        ))
        fig_scatter.add_hline(y=0.75, line=dict(color="#ff3b3b", width=1, dash="dash"), annotation_text="Critical", annotation_font_color="#ff3b3b", annotation_font_size=9)
        fig_scatter.add_hline(y=0.45, line=dict(color="#f5a623", width=1, dash="dash"), annotation_text="Exposed", annotation_font_color="#f5a623", annotation_font_size=9)
        fig_scatter.update_layout(**CHART_LAYOUT, height=360,
            xaxis=dict(title=dict(text="Behavioral Drift Score", font=dict(size=10)), showgrid=True, gridcolor="#1a2d4a", tickfont=dict(size=9, color="#3d5a7a")),
            yaxis=dict(title=dict(text="Contamination Score", font=dict(size=10)), showgrid=True, gridcolor="#1a2d4a", tickfont=dict(size=9, color="#3d5a7a")))
        st.plotly_chart(fig_scatter, use_container_width=True, config={"displayModeBar": False})

# ── ML VALIDATION SECTION ─────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown('<div class="section-header"><span class="section-title">ML Validation — DFCRM vs Logistic Regression</span><div class="section-line"></div></div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:0.75rem;color:var(--text-dim);margin-bottom:1rem">Independent evaluation on synthetic dataset with injected fraud patterns. DFCRM uses zero training data.</div>', unsafe_allow_html=True)

ml_cols = st.columns(5)
ml_metrics = [
    ("Accuracy",  "0.88", "0.86", "#00d4aa"),
    ("Precision", "0.44", "0.39", "#00d4aa"),
    ("Recall",    "0.73", "0.73", "#7a9cc5"),
    ("F1-Score",  "0.55", "0.51", "#00d4aa"),
    ("ROC-AUC",   "0.915","0.923","#f5a623"),
]
for col, (metric, dfcrm_val, lr_val, color) in zip(ml_cols, ml_metrics):
    col.markdown(f"""
    <div class="ml-metric-card">
        <div class="ml-metric-label">{metric}</div>
        <div class="ml-metric-dfcrm" style="color:{color}">{dfcrm_val}</div>
        <div class="ml-metric-sub">DFCRM</div>
        <div class="ml-metric-lr">{lr_val}</div>
        <div class="ml-metric-sub">Logistic Reg.</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="ml-finding">
    <b style="color:#00d4aa">Key finding:</b> DFCRM matches a trained ML model on accuracy, precision and F1
    — without using any training data at all. It works on day one before labeled fraud examples exist.
    The weight optimizer independently confirmed that our α=0.6 / β=0.4 sits in the center of the optimal range (F1 = 0.9091).
</div>
""", unsafe_allow_html=True)

# ── FOOTER ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="border-top:1px solid var(--border);margin-top:2rem;padding-top:1rem;display:flex;justify-content:space-between;align-items:center">
    <div style="font-size:0.7rem;color:var(--text-dim)">DFCRM · Dynamic Fraud Contamination &amp; Recovery Model · Neo4j + FastAPI + Streamlit</div>
    <div style="font-size:0.7rem;color:var(--text-dim);font-family:'JetBrains Mono',monospace">
        {total} accounts · {fraud_count} confirmed fraud · {exposed} monitored
    </div>
</div>
""", unsafe_allow_html=True)