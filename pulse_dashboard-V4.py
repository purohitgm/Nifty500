"""
Pulse v3 — Professional-Grade Nifty Analytics Dashboard
Tabs: Overview · RRG · Screener · Breadth · FII/DII · Watchlist · Alerts
"""

import math, time
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from data_fetcher import (
    fetch_chart, fetch_chart_nse_fallback, fetch_all_sectors, fetch_indices,
    fetch_sector_data, fetch_screener, fetch_fii_dii,
    fetch_breadth_universe, fetch_sector_correlation, fetch_watchlist_stocks,
    is_market_open,
)
from technical_indicators import (
    detect_nr7, detect_nr4, calculate_ema, calculate_rsi, calculate_volume_profile,
    calculate_atr_pct,
)
from watchlist import (
    init_db, add_to_watchlist, remove_from_watchlist, get_watchlist, is_in_watchlist,
    get_all_rrg_trails, get_all_alerts, get_unseen_alerts, mark_alerts_seen,
    unseen_alert_count, clear_old_alerts,
)

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
AUTO_REFRESH = 60

st.set_page_config(page_title="Pulse · Nifty Analytics", page_icon="⚡",
                   layout="wide", initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
html,body,[data-testid="stAppViewContainer"]{background:#060a0f!important;font-family:'Inter',sans-serif}
[data-testid="stHeader"]{background:#060a0f!important}
.block-container{padding:.4rem 1.4rem 2rem!important;max-width:100%!important}
[data-testid="stTabs"] button{color:#8b949e!important;font-size:.8rem!important;font-weight:600!important;letter-spacing:.04em;padding:7px 16px!important;border:none!important;background:transparent!important;border-radius:6px 6px 0 0!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#f0a500!important;background:#0d1117!important;border-bottom:2px solid #f0a500!important}
div[data-testid="metric-container"]{background:#0d1117!important;border:1px solid #21262d!important;border-radius:8px!important;padding:11px 13px!important}
div[data-testid="metric-container"] label{color:#8b949e!important;font-size:.68rem!important;font-weight:700!important;letter-spacing:.07em!important;text-transform:uppercase}
div[data-testid="metric-container"] [data-testid="metric-value"]{color:#e6edf3!important;font-size:1.1rem!important;font-weight:700!important;font-family:'JetBrains Mono',monospace!important}
[data-testid="metric-delta"]{font-size:.75rem!important;font-weight:700!important}
[data-testid="metric-delta"] svg{display:none}
details>summary{background:#0d1117!important;border:1px solid #21262d!important;border-radius:8px!important;padding:9px 13px!important;color:#e6edf3!important;font-weight:600!important;font-size:.82rem!important}
details[open]>summary{border-radius:8px 8px 0 0!important}
details>div{background:#0d1117!important;border:1px solid #21262d!important;border-top:none!important;border-radius:0 0 8px 8px!important;padding:13px!important}
[data-testid="stButton"] button{background:#161b22!important;color:#e6edf3!important;border:1px solid #30363d!important;border-radius:6px!important;font-size:.78rem!important;font-weight:600!important;padding:5px 13px!important;transition:all .2s!important}
[data-testid="stButton"] button:hover{background:#21262d!important;border-color:#f0a500!important;color:#f0a500!important}
[data-testid="stSelectbox"]>div>div{background:#0d1117!important;border:1px solid #30363d!important;border-radius:6px!important;color:#e6edf3!important;font-size:.8rem!important}
[data-testid="stSlider"]>div>div>div{background:#f0a500!important}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:#0d1117}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:2px}
.ticker-wrap{overflow:hidden;background:#0d1117;border-top:1px solid #21262d;border-bottom:1px solid #21262d;padding:5px 0;margin:0 -1.4rem 10px;white-space:nowrap}
.ticker-inner{display:inline-block;animation:ticker 50s linear infinite}
@keyframes ticker{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.ticker-item{display:inline-block;padding:0 24px;font-family:'JetBrains Mono',monospace;font-size:.76rem;font-weight:600}
.live-dot{width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 0 rgba(34,197,94,.6);animation:pdot 2s ease-in-out infinite;display:inline-block}
.mkt-closed-dot{width:7px;height:7px;border-radius:50%;background:#ef4444;display:inline-block}
@keyframes pdot{0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,.5)}50%{box-shadow:0 0 0 6px rgba(34,197,94,0)}}
.pulse-logo{font-size:1.45rem;font-weight:800;letter-spacing:-.03em;color:#f0a500;font-family:'Inter',sans-serif}
.pulse-logo span{color:#e6edf3}
.section-hdr{font-size:.68rem;font-weight:700;color:#8b949e;letter-spacing:.1em;text-transform:uppercase;border-left:3px solid #f0a500;padding-left:8px;margin:12px 0 7px}
.alert-badge{background:#ef4444;color:#fff;border-radius:10px;padding:1px 7px;font-size:.68rem;font-weight:800;margin-left:5px;vertical-align:middle}
.heat-cell{border-radius:8px;padding:13px 11px;position:relative;overflow:hidden;transition:transform .15s,box-shadow .15s;cursor:pointer;border:1px solid rgba(255,255,255,.06)}
.heat-cell:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.5)}
.heat-shine{position:absolute;top:0;left:0;right:0;height:38%;background:linear-gradient(to bottom,rgba(255,255,255,.07),transparent);border-radius:8px 8px 0 0;pointer-events:none}
.idx-card{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px 13px;position:relative;overflow:hidden}
.sig{display:inline-block;padding:3px 8px;border-radius:4px;font-size:.7rem;font-weight:700;margin:2px}
.sig-nr7{background:#431407;color:#fb923c;border:1px solid #7c2d12}
.sig-nr4{background:#3f1010;color:#fca5a5;border:1px solid #991b1b}
.sig-vcp{background:#1e1030;color:#c084fc;border:1px solid #6d28d9}
.sig-pp{background:#052e16;color:#86efac;border:1px solid #166534}
.sig-rsdiv{background:#082f49;color:#7dd3fc;border:1px solid #0369a1}
.sig-minervini{background:#2a1600;color:#fde68a;border:1px solid #d97706}
.sig-earnings{background:#0f172a;color:#f472b6;border:1px solid #be185d}
.sig-warn{background:#1c0a0a;color:#fca5a5;border:1px solid #7f1d1d}
.grade-A{background:#052e16;color:#4ade80;border:1px solid #166534;border-radius:12px;padding:2px 10px;font-weight:800;font-size:.76rem}
.grade-B{background:#431407;color:#fb923c;border:1px solid #7c2d12;border-radius:12px;padding:2px 10px;font-weight:800;font-size:.76rem}
.grade-C{background:#0f172a;color:#94a3b8;border:1px solid #1e293b;border-radius:12px;padding:2px 10px;font-weight:800;font-size:.76rem}
.stock-card{background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:18px;margin-top:10px}
.ma-row{display:flex;gap:8px}
.ma-card{flex:1;background:#161b22;border-radius:6px;padding:7px 10px;border:1px solid #21262d}
.ma-lbl{font-size:.65rem;color:#8b949e;font-weight:700}
.ma-val{font-size:.83rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:#e6edf3;margin-top:2px}
.ma-stat{font-size:.68rem;font-weight:700;margin-top:2px}
.above{color:#4ade80}.below{color:#f87171}
.ema-strip{display:flex;gap:7px;flex-wrap:wrap}
.ema-chip{background:#161b22;border:1px solid #21262d;border-radius:5px;padding:5px 9px}
.ema-lbl{font-size:.6rem;font-weight:700}
.ema-val{font-size:.78rem;font-weight:600;font-family:'JetBrains Mono',monospace;color:#e6edf3}
.range-bar{background:linear-gradient(90deg,#f87171 0%,#fbbf24 50%,#4ade80 100%);height:6px;border-radius:3px;position:relative;margin:6px 0}
.range-dot{position:absolute;top:50%;transform:translate(-50%,-50%);width:13px;height:13px;border-radius:50%;background:#fff;border:2px solid #060a0f;box-shadow:0 0 0 2px #f0a500}
.filter-active{background:#1c1205;border:1px solid #f0a500;border-radius:20px;padding:3px 11px;font-size:.7rem;color:#f0a500;font-weight:700;display:inline-block;margin:2px}
.corr-positive{color:#4ade80;font-weight:700}
.corr-negative{color:#f87171;font-weight:700}
.corr-neutral{color:#8b949e}
.alert-row{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 12px;margin:4px 0;display:flex;align-items:center;gap:10px}
.pulse-divider{border:none;border-top:1px solid #21262d;margin:8px 0}
.pcr-bull{color:#4ade80;font-weight:800;font-size:1.1rem;font-family:'JetBrains Mono',monospace}
.pcr-bear{color:#f87171;font-weight:800;font-size:1.1rem;font-family:'JetBrains Mono',monospace}
.pcr-neu{color:#fbbf24;font-weight:800;font-size:1.1rem;font-family:'JetBrains Mono',monospace}
.wl-row{background:#0d1117;border:1px solid #21262d;border-radius:7px;padding:10px 14px;margin:4px 0;display:flex;align-items:center;justify-content:space-between}
</style>
""", unsafe_allow_html=True)

# ── Plotly theme ──────────────────────────────────────────────────────────────
PT = dict(paper_bgcolor="#060a0f", plot_bgcolor="#0d1117",
          font=dict(color="#e6edf3", family="JetBrains Mono, monospace", size=11))

def gc(r, g, b): return f"rgb({r},{g},{b})"

# ── Helpers ───────────────────────────────────────────────────────────────────
def fp(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return "—"
    return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"
def fi(v): return f"₹{v:,.2f}" if v else "—"
def pc(v): return "#4ade80" if v >= 0 else "#f87171"
def rrg_c(q): return {"Leading":"#22c55e","Weakening":"#eab308","Lagging":"#ef4444","Improving":"#3b82f6"}.get(q,"#8b949e")
def heat_bg(c):
    if c>=2: return "linear-gradient(135deg,#065f46,#047857)"
    if c>=1: return "linear-gradient(135deg,#047857,#059669)"
    if c>=.5:return "linear-gradient(135deg,#064e3b,#047857)"
    if c>=0: return "linear-gradient(135deg,#062316,#083d27)"
    if c>=-.5:return "linear-gradient(135deg,#2d0707,#3f0d0d)"
    if c>=-1: return "linear-gradient(135deg,#450a0a,#7f1d1d)"
    return            "linear-gradient(135deg,#7f1d1d,#991b1b)"
def rsi_gc(r):
    if math.isnan(r): return "#8b949e"
    return "#f59e0b" if r>=70 else "#3b82f6" if r<=30 else "#4ade80"

# ── Auto-refresh ──────────────────────────────────────────────────────────────
def init_state():
    defaults = {"last_refresh": time.time(), "refresh_count": 0,
                "selected_sector": None, "selected_stock": None,
                "active_tab": 0}
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

# ── Auto-refresh via st.fragment (Streamlit 1.37+) ────────────────────────────
# This is the ONLY reliable way to auto-refresh in Streamlit without user
# interaction. check_refresh() + time.time() only runs on user events.
@st.fragment(run_every=AUTO_REFRESH)
def _auto_refresh_fragment():
    """
    Runs every AUTO_REFRESH seconds on a browser-side timer managed by
    Streamlit's fragment scheduler. On each tick (except the very first),
    clears cache and triggers a full app rerun.
    """
    if st.session_state.get("_frag_boot", False):
        st.cache_data.clear()
        st.session_state.refresh_count = st.session_state.get("refresh_count", 0) + 1
        st.session_state.last_refresh  = time.time()
        st.rerun()                       # full-app rerun, not just fragment
    st.session_state["_frag_boot"] = True


def render_countdown():
    """
    Live JavaScript countdown ring that ticks every second in the browser.
    Uses st.components.v1.html() so the JS actually executes (unlike
    st.markdown which strips <script> tags).
    The ring drains from full (60s) to empty (0s), then holds.
    """
    mkt    = is_market_open()
    dot_c  = "#22c55e" if mkt else "#ef4444"
    status = "LIVE" if mkt else "CLOSED"
    elapsed = int(time.time() - st.session_state.get("last_refresh", time.time()))
    remaining = max(0, AUTO_REFRESH - elapsed)

    components.html(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&display=swap');
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; }}
      .wrap {{
        display: flex; align-items: center; gap: 12px;
        font-family: 'JetBrains Mono', monospace;
      }}
      .status-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        background: {dot_c};
        {'animation: pdot 2s ease-in-out infinite;' if mkt else ''}
        flex-shrink: 0;
      }}
      @keyframes pdot {{
        0%,100% {{ box-shadow: 0 0 0 0 {dot_c}80; }}
        50%      {{ box-shadow: 0 0 0 6px {dot_c}00; }}
      }}
      .status-lbl {{
        font-size: 10px; font-weight: 700; color: #8b949e;
        letter-spacing: .07em; line-height: 1;
      }}
      .ist-time {{
        font-size: 10px; color: #8b949e;
      }}
      .ring-wrap {{
        position: relative; width: 38px; height: 38px; flex-shrink: 0;
      }}
      svg {{ transform: rotate(-90deg); display: block; }}
      .bg {{ fill: none; stroke: #21262d; stroke-width: 3.5; }}
      .fg {{
        fill: none; stroke: #f0a500; stroke-width: 3.5;
        stroke-linecap: round; stroke-dasharray: 100;
      }}
      .lbl {{
        position: absolute; top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        font-size: 9px; font-weight: 700; color: #f0a500;
      }}
    </style>

    <div class="wrap">
      <div class="status-dot"></div>
      <div>
        <div class="status-lbl">{status}</div>
        <div class="ist-time" id="ist-time">—</div>
      </div>
      <div class="ring-wrap">
        <svg viewBox="0 0 36 36" width="38" height="38">
          <circle class="bg" cx="18" cy="18" r="15.9"/>
          <circle class="fg" cx="18" cy="18" r="15.9" id="ring"/>
        </svg>
        <div class="lbl" id="lbl">{remaining:02d}</div>
      </div>
    </div>

    <script>
      const TOTAL   = {AUTO_REFRESH};
      let   rem     = {remaining};

      function pad(n) {{ return String(n).padStart(2,'0'); }}

      function updateIST() {{
        const now = new Date();
        // UTC+5:30
        const ist = new Date(now.getTime() + (5*60+30)*60000);
        document.getElementById('ist-time').textContent =
          pad(ist.getUTCHours())+':'+pad(ist.getUTCMinutes())+':'+pad(ist.getUTCSeconds())+' IST';
      }}

      function tick() {{
        // Ring: stroke-dashoffset = 100 when empty, 0 when full
        const dashOff = 100 - Math.round((rem / TOTAL) * 100);
        document.getElementById('ring').style.strokeDashoffset = dashOff;
        document.getElementById('lbl').textContent = pad(rem);

        updateIST();

        if (rem > 0) {{
          rem--;
          setTimeout(tick, 1000);
        }} else {{
          // Show 00 and pulse ring color to indicate pending refresh
          document.getElementById('ring').style.stroke = '#ef4444';
        }}
      }}

      tick();
    </script>
    """, height=48, scrolling=False)

# ── Ticker tape ───────────────────────────────────────────────────────────────
def render_ticker(indices):
    items = []
    for idx in indices:
        c = pc(idx["change_pct"]); a = "▲" if idx["change_pct"]>=0 else "▼"
        items.append(f'<span class="ticker-item"><span style="color:#8b949e">{idx["name"]}</span>'
            f'&nbsp;<span style="color:#e6edf3;font-weight:700">{idx["price"]:,.0f}</span>'
            f'&nbsp;<span style="color:{c}">{a} {fp(idx["change_pct"])}</span></span>')
    inner = "".join(items * 2)
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-inner">{inner}</div></div>', unsafe_allow_html=True)

# ── Index cards ───────────────────────────────────────────────────────────────
def render_index_cards(indices):
    KEY = ("NIFTY 50","NIFTY BANK","NIFTY IT","NIFTY PHARMA","NIFTY AUTO","NIFTY METAL")
    display = [i for i in indices if i["name"] in KEY][:6] or indices[:6]
    cols = st.columns(len(display))
    for col, idx in zip(cols, display):
        c = pc(idx["change_pct"]); rsi = idx.get("rsi", float("nan"))
        rc = rsi_gc(rsi); rs = f"{rsi:.0f}" if not math.isnan(rsi) else "—"
        h52, l52 = idx.get("week52_high",0), idx.get("week52_low",0)
        bp = int((idx["price"]-l52)/max(1,h52-l52)*100) if h52>l52 else 50
        col.markdown(f"""<div class="idx-card">
          <div style="font-size:.67rem;color:#8b949e;font-weight:700;letter-spacing:.06em;text-transform:uppercase">{idx['name']}</div>
          <div style="font-size:1.15rem;font-weight:700;color:#e6edf3;font-family:'JetBrains Mono',monospace;margin:3px 0">{idx['price']:,.0f}</div>
          <div style="font-size:.77rem;font-weight:700;color:{c};font-family:'JetBrains Mono',monospace">{fp(idx['change_pct'])}&nbsp;<span style="color:#8b949e;font-size:.65rem">{idx['change']:+,.0f}</span></div>
          <div style="font-size:.65rem;color:#8b949e;margin-top:3px">RSI <span style="color:{rc};font-weight:700">{rs}</span></div>
          <div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:#21262d">
            <div style="height:100%;width:{bp}%;background:{c};opacity:.7;border-radius:0 0 8px 0"></div>
          </div>
        </div>""", unsafe_allow_html=True)

# ── Sector heatmap grid ───────────────────────────────────────────────────────
def render_heatmap_grid(sectors):
    cols = st.columns(5)
    for i, s in enumerate(sectors):
        bg = heat_bg(s["change"]); qc = rrg_c(s.get("rrg_quadrant","Lagging"))
        mom = int(s.get("momentum",50))
        with cols[i % 5]:
            st.markdown(f"""<div class="heat-cell" style="background:{bg};min-height:105px">
              <div class="heat-shine"></div>
              <div style="font-size:.8rem;font-weight:700;color:#fff;margin-bottom:3px">{s['name']}</div>
              <div style="font-size:1.2rem;font-weight:800;color:#fff;font-family:'JetBrains Mono',monospace">{fp(s['change'])}</div>
              <div style="display:flex;gap:12px;margin-top:6px">
                <span style="font-size:.67rem;color:rgba(255,255,255,.7)">RSI <b style="color:#fff">{s['rsi']:.0f}</b></span>
                <span style="font-size:.67rem;color:rgba(255,255,255,.7)">Breadth <b style="color:#fff">{s['breadth']:.0f}%</b></span>
              </div>
              <span style="font-size:.65rem;padding:2px 6px;background:rgba(0,0,0,.35);color:{qc};border-radius:3px;display:inline-block;margin-top:4px">{s.get('rrg_quadrant','')}</span>
              <div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:rgba(0,0,0,.3)">
                <div style="height:100%;width:{mom}%;background:rgba(255,255,255,.5);border-radius:2px"></div>
              </div>
            </div>""", unsafe_allow_html=True)
            if st.button("⤵", key=f"hd_{s['name']}", use_container_width=True):
                st.session_state.selected_sector = s["name"]
                st.rerun()

# ── Treemap heatmap ───────────────────────────────────────────────────────────
def render_treemap(sectors):
    colors_map = {">=2":"#065f46",">=1":"#047857",">=0.5":"#059669",">=0":"#083d27",
                  "<0":"#3f0d0d","<-1":"#7f1d1d","<-2":"#991b1b"}
    def get_c(ch):
        if ch>=2: return "#065f46"
        if ch>=1: return "#047857"
        if ch>=.5:return "#059669"
        if ch>=0: return "#083d27"
        if ch>=-.5:return "#3f0d0d"
        if ch>=-1: return "#7f1d1d"
        return "#991b1b"
    fig = go.Figure(go.Treemap(
        labels=[s["name"] for s in sectors],
        parents=[""] * len(sectors),
        values=[max(1, s["stock_count"]) for s in sectors],
        text=[f"<b>{s['name']}</b><br>{fp(s['change'])}<br>RSI {s['rsi']:.0f} · {s.get('rrg_quadrant','')}" for s in sectors],
        textinfo="text",
        marker=dict(colors=[get_c(s["change"]) for s in sectors], line=dict(width=2, color="#060a0f")),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
    ))
    fig.update_layout(**PT, margin=dict(l=0,r=0,t=0,b=0), height=300)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

# ── Candlestick with EMA + Volume Profile ────────────────────────────────────
def render_candlestick(ohlcv, symbol, show_vp=True, timeframe="6mo"):
    if not ohlcv: return go.Figure()
    df = pd.DataFrame(ohlcv); df["date"] = pd.to_datetime(df["date"])
    closes  = df["close"].tolist(); volumes = df["volume"].tolist()
    ema10 = calculate_ema(closes, 10)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)
    nr7d  = [df["date"].iloc[i] for i,v in enumerate(detect_nr7(ohlcv)) if v]
    nr7l  = [df["low"].iloc[i]*0.997 for i,v in enumerate(detect_nr7(ohlcv)) if v]
    nr4d  = [df["date"].iloc[i] for i,v in enumerate(detect_nr4(ohlcv)) if v]
    nr4l  = [df["low"].iloc[i]*0.994 for i,v in enumerate(detect_nr4(ohlcv)) if v]
    vol_c = ["#4ade80" if c>=o else "#f87171" for c,o in zip(closes, df["open"].tolist())]

    cols_cnt = 2 if show_vp else 1
    col_widths = [0.82, 0.18] if show_vp else [1.0]
    fig = make_subplots(rows=2, cols=cols_cnt, shared_xaxes=True,
        row_heights=[0.73,0.27], column_widths=col_widths, vertical_spacing=0.01,
        horizontal_spacing=0.01)

    fig.add_trace(go.Candlestick(x=df["date"],open=df["open"],high=df["high"],
        low=df["low"],close=closes,name=symbol.replace(".NS",""),
        increasing=dict(line=dict(color="#4ade80",width=1),fillcolor="#4ade80"),
        decreasing=dict(line=dict(color="#f87171",width=1),fillcolor="#f87171")),row=1,col=1)

    for ema,color,name in [(ema10,"#38bdf8","EMA10"),(ema21,"#a78bfa","EMA21"),(ema50,"#fb923c","EMA50")]:
        valid = [(d,v) for d,v in zip(df["date"],ema) if not math.isnan(v)]
        if valid:
            xs,ys = zip(*valid)
            fig.add_trace(go.Scatter(x=list(xs),y=list(ys),mode="lines",
                line=dict(color=color,width=1.2),name=name,opacity=.85),row=1,col=1)

    if nr7d: fig.add_trace(go.Scatter(x=nr7d,y=nr7l,mode="markers",
        marker=dict(symbol="triangle-up",size=9,color="#f59e0b"),name="NR7"),row=1,col=1)
    if nr4d: fig.add_trace(go.Scatter(x=nr4d,y=nr4l,mode="markers",
        marker=dict(symbol="triangle-up",size=7,color="#f97316"),name="NR4"),row=1,col=1)

    fig.add_trace(go.Bar(x=df["date"],y=volumes,name="Volume",
        marker_color=vol_c,opacity=.65),row=2,col=1)

    # Volume Profile
    if show_vp:
        vp = calculate_volume_profile(ohlcv, bins=22)
        max_v = vp["max_volume"] or 1
        for b in vp["bins"]:
            norm = b["volume"] / max_v
            color = "#f0a500" if abs(b["price"] - vp["poc"]) < (vp["poc"] * 0.005) else \
                    "#4ade8060" if b["price"] >= vp["val"] and b["price"] <= vp["vah"] else "#30363d80"
            fig.add_trace(go.Bar(x=[norm],y=[b["price"]],orientation="h",
                marker_color=color,showlegend=False,hoverinfo="skip",
                width=(vp["bins"][1]["price"]-vp["bins"][0]["price"])*0.9 if len(vp["bins"])>1 else 10
            ),row=1,col=2)
        for price,label,color in [(vp["poc"],"POC","#f0a500"),(vp["vah"],"VAH","#4ade8080"),(vp["val"],"VAL","#4ade8080")]:
            fig.add_hline(y=price,line=dict(color=color,dash="dot",width=1),row=1,col=1,
                annotation_text=label,annotation_font_size=9,annotation_font_color=color,
                annotation_position="left")

    fig.update_layout(**PT,height=440,margin=dict(l=10,r=10,t=10,b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",y=1.04,x=0,bgcolor="rgba(0,0,0,0)",
            font=dict(size=9),itemsizing="constant"),hovermode="x unified")
    for r in [1,2]:
        fig.update_xaxes(gridcolor="#1a2030",showgrid=True,row=r,col=1,zeroline=False)
        fig.update_yaxes(gridcolor="#1a2030",showgrid=True,row=r,col=1,zeroline=False,tickfont=dict(size=9))
    if show_vp:
        fig.update_xaxes(showgrid=False,row=1,col=2,showticklabels=False)
        fig.update_yaxes(showgrid=False,row=1,col=2,showticklabels=False)
    return fig

# ── RSI Gauge ─────────────────────────────────────────────────────────────────
def rsi_gauge(rsi):
    c = rsi_gc(rsi)
    fig = go.Figure(go.Indicator(mode="gauge+number",
        value=rsi if not math.isnan(rsi) else 50,
        gauge=dict(axis=dict(range=[0,100],tickwidth=1,tickcolor="#30363d",
            tickfont=dict(size=9,color="#8b949e"),tickvals=[0,30,50,70,100]),
            bar=dict(color=c,thickness=.3),bgcolor="#0d1117",borderwidth=0,
            steps=[dict(range=[0,30],color="#082f49"),dict(range=[30,70],color="#161b22"),
                   dict(range=[70,100],color="#431407")],
            threshold=dict(line=dict(color=c,width=2),thickness=.75,value=rsi)),
        number=dict(font=dict(size=22,color=c,family="JetBrains Mono")),
        title=dict(text="RSI (14)",font=dict(size=10,color="#8b949e")),
        domain=dict(x=[0,1],y=[0,1])))
    fig.update_layout(**PT,height=130,margin=dict(l=10,r=10,t=20,b=0))
    return fig

def momentum_donut(score):
    c = "#4ade80" if score>=70 else "#f59e0b" if score>=40 else "#f87171"
    fig = go.Figure(go.Pie(values=[score,100-score],hole=.72,showlegend=False,
        marker=dict(colors=[c,"#161b22"]),textinfo="none"))
    fig.add_annotation(text=f"<b>{score:.0f}</b>",x=.5,y=.5,showarrow=False,
        font=dict(size=20,color=c,family="JetBrains Mono"))
    fig.add_annotation(text="MOM",x=.5,y=.22,showarrow=False,font=dict(size=9,color="#8b949e"))
    fig.update_layout(**PT,height=130,margin=dict(l=0,r=0,t=10,b=0))
    return fig

def rs_rank_gauge(rank):
    c = "#4ade80" if rank>=80 else "#f59e0b" if rank>=50 else "#f87171"
    fig = go.Figure(go.Indicator(mode="gauge+number",value=rank,
        gauge=dict(axis=dict(range=[0,99],tickfont=dict(size=9,color="#8b949e"),
            tickvals=[0,25,50,75,99]),
            bar=dict(color=c,thickness=.3),bgcolor="#0d1117",borderwidth=0,
            steps=[dict(range=[0,50],color="#1a0a0a"),dict(range=[50,80],color="#161b22"),
                   dict(range=[80,99],color="#052e16")]),
        number=dict(font=dict(size=22,color=c,family="JetBrains Mono")),
        title=dict(text="RS Rank",font=dict(size=10,color="#8b949e")),
        domain=dict(x=[0,1],y=[0,1])))
    fig.update_layout(**PT,height=130,margin=dict(l=10,r=10,t=20,b=0))
    return fig

# ── Stock Detail ──────────────────────────────────────────────────────────────
def render_stock_detail(stock, show_add_watchlist=True):
    sym = stock["symbol"].replace(".NS",""); price = stock["price"]
    chg = stock["change_pct"]; cc = pc(chg)
    rsi = stock.get("rsi",float("nan")); mom = stock.get("momentum",0)
    volr = stock.get("vol_ratio",1); rs = stock.get("rs",0)
    rs_rank = stock.get("rs_rank",50); grade = stock.get("grade","—")
    gcls = f"grade-{grade}" if grade in "ABC" else "grade-C"
    rrg_q = stock.get("rrg_quadrant","—"); qc = rrg_c(rrg_q)

    # Badge row
    badges = ""
    for flag,cls,label in [
        (stock.get("is_nr7"),"sig-nr7","NR7"),(stock.get("is_nr4"),"sig-nr4","NR4"),
        (stock.get("is_vcp"),"sig-vcp","VCP"),(stock.get("is_pocket_pivot"),"sig-pp","Pocket Pivot"),
        (stock.get("is_rs_div"),"sig-rsdiv","RS Divergence"),
        (stock.get("minervini_passes"),"sig-minervini","⭐ Minervini"),
        (stock.get("has_earnings"),"sig-earnings","📅 Earnings <7d"),
        (stock.get("data_gap"),"sig-warn","⚠ Data Gap"),
    ]:
        if flag: badges += f'<span class="sig {cls}">{label}</span>'

    wl_in = is_in_watchlist(stock["symbol"])

    st.markdown(f"""<div class="stock-card">
      <div style="display:flex;align-items:flex-start;justify-content:space-between">
        <div>
          <div style="display:flex;align-items:center;gap:9px">
            <div style="font-size:1.55rem;font-weight:800;color:#e6edf3;font-family:'JetBrains Mono',monospace">{sym}</div>
            <span class="{gcls}">{grade}</span>
            <span style="background:rgba(0,0,0,.3);color:{qc};padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:700;border:1px solid {qc}40">{rrg_q}</span>
            <span style="font-size:.7rem;color:#8b949e">RS#{rs_rank}</span>
          </div>
          <div style="font-size:.8rem;color:#8b949e;margin-top:1px">{stock.get('name','')}</div>
          <div style="margin-top:5px">
            <span style="font-size:1.9rem;font-weight:700;color:#e6edf3;font-family:'JetBrains Mono',monospace">{fi(price)}</span>
            <span style="color:{cc};font-size:.95rem;font-weight:700;font-family:'JetBrains Mono',monospace;margin-left:10px">{fp(chg)}</span>
          </div>
          <div style="margin-top:7px">{badges or '<span style="color:#8b949e;font-size:.73rem">No pattern signals today</span>'}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:.66rem;color:#8b949e">Vol Ratio</div>
          <div style="font-size:1.25rem;font-weight:700;color:{'#4ade80' if volr>1.5 else '#e6edf3'};font-family:'JetBrains Mono',monospace">{volr:.2f}×</div>
          <div style="font-size:.66rem;color:#8b949e;margin-top:6px">Rel. Strength</div>
          <div style="font-size:.95rem;font-weight:700;color:{pc(rs)};font-family:'JetBrains Mono',monospace">{rs:+.1f}%</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Watchlist button
    if show_add_watchlist:
        wl_col, _ = st.columns([1,5])
        with wl_col:
            if wl_in:
                if st.button(f"⭐ Remove from Watchlist", key=f"wl_{sym}"):
                    remove_from_watchlist(stock["symbol"])
                    st.rerun()
            else:
                if st.button(f"☆ Add to Watchlist", key=f"wl_{sym}"):
                    add_to_watchlist(stock["symbol"], stock.get("name",""), stock.get("sector",""))
                    st.rerun()

    # Minervini detail
    mv = stock.get("minervini_detail",{})
    if mv.get("criteria_met",0) >= 3:
        crits = mv.get("criteria",{})
        crit_html = " ".join([
            f'<span style="color:{"#4ade80" if v else "#f87171"};font-size:.72rem;margin-right:6px">{"✓" if v else "✗"} {k.replace("_"," ")}</span>'
            for k,v in crits.items()
        ])
        st.markdown(f'<div style="background:#1a0e00;border:1px solid #d97706;border-radius:6px;padding:8px 12px;margin:8px 0">'
            f'<span style="color:#fde68a;font-size:.72rem;font-weight:700">MINERVINI TEMPLATE — {mv.get("criteria_met",0)}/6 criteria</span><br>'
            f'{crit_html}</div>', unsafe_allow_html=True)

    # Gauges row
    g1, g2, g3, g4 = st.columns([1,1,1,3])
    with g1: st.plotly_chart(rsi_gauge(rsi), use_container_width=True, config={"displayModeBar":False})
    with g2: st.plotly_chart(momentum_donut(mom), use_container_width=True, config={"displayModeBar":False})
    with g3: st.plotly_chart(rs_rank_gauge(rs_rank), use_container_width=True, config={"displayModeBar":False})
    with g4:
        st.markdown('<div class="section-hdr">Moving Averages</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="ma-row">
          {''.join([f'<div class="ma-card"><div class="ma-lbl">{n} DMA</div>'
           f'<div class="ma-val">{v:.1f}</div><div class="ma-stat {"above" if ab else "below"}">{"▲ Above" if ab else "▼ Below"}</div></div>'
           for n,v,ab in [("20",stock.get("dma20",0),stock.get("above20dma",False)),
                          ("50",stock.get("dma50",0),stock.get("above50dma",False)),
                          ("200",stock.get("dma200",0),stock.get("above200dma",False))]])}
        </div>""", unsafe_allow_html=True)
        st.markdown('<div class="section-hdr" style="margin-top:8px">EMA Values</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="ema-strip">
          {''.join([f'<div class="ema-chip"><div class="ema-lbl" style="color:{c}">{n}</div><div class="ema-val">{v:.1f}</div></div>'
           for n,v,c in [("EMA5",stock.get("ema5",0),"#38bdf8"),("EMA10",stock.get("ema10",0),"#38bdf8"),
                         ("EMA21",stock.get("ema21",0),"#a78bfa"),("EMA50",stock.get("ema50",0),"#fb923c")]])}
        </div>""", unsafe_allow_html=True)

    # 52w range
    lo,hi = stock.get("low52w",0), stock.get("high52w",0)
    pp_ = int((price-lo)/max(1,hi-lo)*100) if hi>lo else 50
    st.markdown(f"""<div style="margin:10px 0 5px"><div class="section-hdr">52-Week Range</div>
      <div style="display:flex;align-items:center;gap:9px;margin-top:4px">
        <span style="font-size:.73rem;color:#8b949e;font-family:'JetBrains Mono',monospace;min-width:75px">{fi(lo)}</span>
        <div style="flex:1;position:relative"><div class="range-bar"></div>
          <div class="range-dot" style="left:{pp_}%"></div></div>
        <span style="font-size:.73rem;color:#8b949e;font-family:'JetBrains Mono',monospace;min-width:75px;text-align:right">{fi(hi)}</span>
      </div>
      <div style="text-align:center;font-size:.68rem;color:{pc(chg)};margin-top:2px">{pp_}% of 52w range</div>
    </div>""", unsafe_allow_html=True)

    # Chart with timeframe toggle
    if stock.get("ohlcv"):
        tf_col, _ = st.columns([2,5])
        with tf_col:
            tf = st.radio("Timeframe", ["1M","3M","6M","1Y"], horizontal=True,
                key=f"tf_{sym}", index=2, label_visibility="collapsed")
        tf_map = {"1M":"1mo","3M":"3mo","6M":"6mo","1Y":"1y"}
        tf_range = tf_map[tf]
        if tf_range != "6mo":
            res = fetch_chart(stock["symbol"], tf_range)
            ohlcv_tf = res["ohlcv"] or stock["ohlcv"]
        else:
            ohlcv_tf = stock["ohlcv"]
        st.markdown('<div class="section-hdr">Price Chart — EMA · NR7▲ · NR4▲ · Volume Profile</div>', unsafe_allow_html=True)
        st.plotly_chart(render_candlestick(ohlcv_tf, stock["symbol"]),
            use_container_width=True, config={"displayModeBar":False})

    # External links
    st.markdown(f'<div style="display:flex;gap:10px;margin-top:5px">'
        f'<a href="https://www.screener.in/company/{sym}/" target="_blank" style="font-size:.76rem;color:#f0a500;text-decoration:none;border:1px solid #f0a50040;border-radius:5px;padding:4px 11px">🔗 Screener.in</a>'
        f'<a href="https://in.tradingview.com/chart/?symbol=NSE:{sym}" target="_blank" style="font-size:.76rem;color:#38bdf8;text-decoration:none;border:1px solid #38bdf840;border-radius:5px;padding:4px 11px">📈 TradingView</a>'
        f'<a href="https://chartink.com/stocks/{sym}.html" target="_blank" style="font-size:.76rem;color:#a78bfa;text-decoration:none;border:1px solid #a78bfa40;border-radius:5px;padding:4px 11px">📊 ChartInk</a>'
        f'</div>', unsafe_allow_html=True)

# ── RRG with trails ───────────────────────────────────────────────────────────
def render_rrg(sectors):
    trails = get_all_rrg_trails(max_points=8)
    fig = go.Figure()
    for x0,x1,y0,y1,c in [(100,115,100,115,"rgba(34,197,94,0.07)"),(100,115,85,100,"rgba(234,179,8,0.07)"),
                            (85,100,85,100,"rgba(239,68,68,0.07)"),(85,100,100,115,"rgba(59,130,246,0.07)")]:
        fig.add_shape(type="rect",x0=x0,x1=x1,y0=y0,y1=y1,fillcolor=c,line=dict(width=0),layer="below")

    for s in sectors:
        q=s.get("rrg_quadrant","Lagging"); c=rrg_c(q)
        rx,rm=s.get("rs_ratio",100),s.get("rs_momentum",100)
        # Trail
        trail = trails.get(s["name"],[])
        if len(trail) > 1:
            txs=[t["rs_ratio"] for t in trail]; tys=[t["rs_momentum"] for t in trail]
            alphas=[0.15+0.7*i/max(1,len(trail)-1) for i in range(len(trail))]
            for i in range(len(trail)-1):
                fig.add_trace(go.Scatter(x=txs[i:i+2],y=tys[i:i+2],mode="lines",
                    line=dict(color=c,width=1.5),opacity=alphas[i],showlegend=False,hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=txs[:-1],y=tys[:-1],mode="markers",
                marker=dict(size=5,color=c,opacity=[a*0.6 for a in alphas[:-1]]),
                showlegend=False,hoverinfo="skip"))

        fig.add_trace(go.Scatter(x=[rx],y=[rm],mode="markers+text",
            marker=dict(size=15,color=c,line=dict(width=2.5,color="#060a0f")),
            text=[f"  {s['name']}"],textposition="middle right",
            textfont=dict(size=11,color="#e6edf3",family="Inter"),name=s["name"],
            hovertemplate=f"<b>{s['name']}</b><br>RS-Ratio: {rx:.2f}<br>RS-Momentum: {rm:.2f}<br>{q}<extra></extra>"))

    fig.add_hline(y=100,line=dict(color="#30363d",dash="dot",width=1))
    fig.add_vline(x=100,line=dict(color="#30363d",dash="dot",width=1))
    for x,y,lbl,c in [(86.5,114,"IMPROVING","#3b82f6"),(114,114,"LEADING","#22c55e"),
                       (114,86,"WEAKENING","#eab308"),(86.5,86,"LAGGING","#ef4444")]:
        fig.add_annotation(x=x,y=y,text=lbl,showarrow=False,font=dict(size=8.5,color=c,family="Inter"),opacity=.5)
    fig.update_layout(**PT,xaxis=dict(title="← Lagging  |  RS-Ratio  |  Leading →",gridcolor="#1a2030",
        range=[85,115],title_font=dict(size=10,color="#8b949e"),tickfont=dict(size=9)),
        yaxis=dict(title="RS-Momentum",gridcolor="#1a2030",range=[85,115],
        title_font=dict(size=10,color="#8b949e"),tickfont=dict(size=9)),
        showlegend=False,height=500,margin=dict(l=55,r=30,t=15,b=55),hovermode="closest")
    return fig

# ── FII/DII Chart ─────────────────────────────────────────────────────────────
def render_fii_dii(data):
    if not data: return go.Figure()
    df = pd.DataFrame(data)
    fig = make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[0.6,0.4],vertical_spacing=0.05)
    fig.add_trace(go.Bar(x=df["date"],y=df["fii_net"],name="FII Net",
        marker_color=["#4ade80" if v>=0 else "#f87171" for v in df["fii_net"]]),row=1,col=1)
    fig.add_trace(go.Bar(x=df["date"],y=df["dii_net"],name="DII Net",
        marker_color=["#60a5fa" if v>=0 else "#fbbf24" for v in df["dii_net"]]),row=1,col=1)
    # Cumulative
    df["fii_cum"] = df["fii_net"].cumsum(); df["dii_cum"] = df["dii_net"].cumsum()
    fig.add_trace(go.Scatter(x=df["date"],y=df["fii_cum"],name="FII Cumulative",
        line=dict(color="#4ade80",width=2)),row=2,col=1)
    fig.add_trace(go.Scatter(x=df["date"],y=df["dii_cum"],name="DII Cumulative",
        line=dict(color="#60a5fa",width=2)),row=2,col=1)
    fig.update_layout(**PT,height=420,margin=dict(l=50,r=10,t=20,b=40),barmode="group",
        legend=dict(orientation="h",y=1.05,bgcolor="rgba(0,0,0,0)"))
    for r in [1,2]:
        fig.update_xaxes(gridcolor="#1a2030",row=r,col=1)
        fig.update_yaxes(gridcolor="#1a2030",row=r,col=1,tickfont=dict(size=9))
    return fig

# ── Correlation heatmap ───────────────────────────────────────────────────────
def render_correlation(corr_matrix):
    from nifty_indices import SECTORS
    names = [s["name"] for s in SECTORS]
    z = [[corr_matrix.get((n1,n2),0) for n2 in names] for n1 in names]
    fig = go.Figure(go.Heatmap(z=z,x=names,y=names,
        colorscale=[[0,"#ef4444"],[0.5,"#161b22"],[1,"#22c55e"]],
        zmid=0,zmin=-1,zmax=1,text=[[f"{v:.2f}" for v in row] for row in z],
        texttemplate="%{text}",textfont=dict(size=10),hovertemplate="<b>%{x}</b> vs <b>%{y}</b>: %{z:.3f}<extra></extra>"))
    fig.update_layout(**PT,height=460,margin=dict(l=120,r=20,t=20,b=120),
        xaxis=dict(tickangle=-45,tickfont=dict(size=10)),yaxis=dict(tickfont=dict(size=10)))
    return fig

# ── Breadth Charts ────────────────────────────────────────────────────────────
def render_breadth_charts(history, current_ad, current_hl, current_pma):
    if history:
        df = pd.DataFrame(history)
        fig = make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=0.05,
            subplot_titles=["A/D Net (advances minus declines)",
                            "New 52w Highs vs Lows","% Stocks Above DMA"])
        fig.add_trace(go.Bar(x=df["date"],y=df["advances"]-df["declines"],name="A/D Net",
            marker_color=["#4ade80" if v>=0 else "#f87171" for v in df["advances"]-df["declines"]]),row=1,col=1)
        fig.add_trace(go.Scatter(x=df["date"],y=df["new_highs"],name="New Highs",
            line=dict(color="#4ade80",width=2)),row=2,col=1)
        fig.add_trace(go.Scatter(x=df["date"],y=df["new_lows"],name="New Lows",
            line=dict(color="#f87171",width=2)),row=2,col=1)
        fig.add_trace(go.Scatter(x=df["date"],y=df["pct_above20"],name="% >20DMA",
            line=dict(color="#38bdf8",width=2)),row=3,col=1)
        fig.add_trace(go.Scatter(x=df["date"],y=df["pct_above50"],name="% >50DMA",
            line=dict(color="#a78bfa",width=2,dash="dot")),row=3,col=1)
        fig.add_hline(y=50,row=3,col=1,line=dict(color="#30363d",dash="dash",width=1))
        fig.update_layout(**PT,height=520,margin=dict(l=50,r=10,t=30,b=20),
            legend=dict(orientation="h",y=1.05,bgcolor="rgba(0,0,0,0)"))
        for r in [1,2,3]:
            fig.update_xaxes(gridcolor="#1a2030",row=r,col=1)
            fig.update_yaxes(gridcolor="#1a2030",row=r,col=1,tickfont=dict(size=9))
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    init_state()
    # Schedule automatic 60s refresh (no user interaction needed)
    _auto_refresh_fragment()
    clear_old_alerts(days=7)

    # Header
    h1,h2,h3 = st.columns([3,5,3])
    with h1:
        alert_n = unseen_alert_count()
        badge = f'<span class="alert-badge">{alert_n}</span>' if alert_n else ""
        st.markdown(f'<div style="padding-top:5px"><div class="pulse-logo">⚡ Pulse<span style="opacity:.4">·</span></div>'
            f'<div style="font-size:.68rem;color:#8b949e;letter-spacing:.08em;text-transform:uppercase">Nifty Analytics {badge}</div></div>',
            unsafe_allow_html=True)
    with h3:
        rc1,rc2 = st.columns([3,1])
        with rc1: render_countdown()
        with rc2:
            if st.button("↺",help="Refresh now"):
                st.cache_data.clear(); st.session_state.last_refresh=time.time(); st.rerun()

    # Load core data
    with st.spinner(""):
        indices = fetch_indices()
        sectors = fetch_all_sectors()

    if indices: render_ticker(indices)
    if indices: render_index_cards(indices)
    st.markdown("<div style='height:6px'></div>",unsafe_allow_html=True)

    # Alert count in tab label
    an = unseen_alert_count()
    alert_tab_label = f"  🔔  Alerts {f'({an})' if an else ''}  "

    tabs = st.tabs(["  🗺  Overview  ","  🔄  RRG  ","  🔍  Screener  ",
                     "  📊  Breadth  ","  💰  FII/DII  ",
                     "  ⭐  Watchlist  ", alert_tab_label])

    # ══════════ OVERVIEW ══════════════════════════════════════════════════════
    with tabs[0]:
        selected = st.session_state.selected_sector
        if selected:
            bc,_ = st.columns([1,9])
            with bc:
                if st.button("← Back"):
                    st.session_state.update(selected_sector=None,selected_stock=None); st.rerun()
            with st.spinner(f"Loading {selected}…"):
                detail = fetch_sector_data(selected)
            if detail:
                st.markdown(f'<div style="font-size:1.05rem;font-weight:700;color:#e6edf3;margin-bottom:7px">'
                    f'<span style="color:#f0a500">{selected}</span> Sector</div>',unsafe_allow_html=True)
                m1,m2,m3,m4,m5 = st.columns(5)
                m1.metric("Change",fp(detail["change"])); m2.metric("RSI",f"{detail['rsi']:.1f}")
                m3.metric("Momentum",f"{detail['momentum']:.0f}"); m4.metric("Breadth",f"{detail['breadth']:.0f}%")
                m5.metric("Vol Ratio",f"{detail['vol_ratio']:.2f}×")
                st.markdown('<hr class="pulse-divider"/>',unsafe_allow_html=True)
                if detail["stocks"]:
                    rows=[]
                    for s in detail["stocks"]:
                        rows.append({"Symbol":s["symbol"].replace(".NS",""),"Name":s["name"],
                            "Price":s["price"],"Chg%":s["change_pct"],"RSI":s["rsi"],
                            "Mom":s["momentum"],"VolR":s["vol_ratio"],"RS#":s.get("rs_rank",50),
                            "RRG":s["rrg_quadrant"],"20D":s["above20dma"],"50D":s["above50dma"],
                            "⭐":is_in_watchlist(s["symbol"]),
                            "Signals":" ".join(filter(None,["NR7" if s["is_nr7"] else "",
                                "NR4" if s["is_nr4"] else "","VCP" if s["is_vcp"] else "",
                                "PP" if s["is_pocket_pivot"] else "","RS↑" if s["is_rs_div"] else "",
                                "MV" if s.get("minervini_passes") else "","📅" if s.get("has_earnings") else ""]))or"—"})
                    df=pd.DataFrame(rows)
                    sel=st.dataframe(df,use_container_width=True,hide_index=True,
                        on_select="rerun",selection_mode="single-row",
                        column_config={"Price":st.column_config.NumberColumn(format="₹%.2f"),
                            "Chg%":st.column_config.NumberColumn(format="%.2f%%"),
                            "RSI":st.column_config.NumberColumn(format="%.1f"),
                            "Mom":st.column_config.ProgressColumn(min_value=0,max_value=100,format="%.0f"),
                            "VolR":st.column_config.NumberColumn(format="%.2f×"),
                            "20D":st.column_config.CheckboxColumn(),"50D":st.column_config.CheckboxColumn(),
                            "⭐":st.column_config.CheckboxColumn()})
                    if sel.selection.rows:
                        render_stock_detail(detail["stocks"][sel.selection.rows[0]])
        else:
            view = st.radio("",["Grid","Treemap"],horizontal=True,label_visibility="collapsed")
            st.markdown('<div class="section-hdr">Sector Heatmap — ⤵ to drill in</div>',unsafe_allow_html=True)
            if view=="Treemap": render_treemap(sectors)
            else: render_heatmap_grid(sectors)
            st.markdown('<hr class="pulse-divider"/>',unsafe_allow_html=True)
            st.markdown('<div class="section-hdr">Sector Summary — click row to drill in</div>',unsafe_allow_html=True)
            df=pd.DataFrame([{"Sector":s["name"],"Change%":s["change"],"RSI":s["rsi"],
                "Momentum":s["momentum"],"Breadth%":s["breadth"],"VolRatio":s["vol_ratio"],
                "RRG":s.get("rrg_quadrant","—"),"Stocks":s.get("stock_count",0)} for s in sectors])
            sel=st.dataframe(df,use_container_width=True,hide_index=True,
                on_select="rerun",selection_mode="single-row",
                column_config={"Change%":st.column_config.NumberColumn(format="%.2f%%"),
                    "RSI":st.column_config.NumberColumn(format="%.1f"),
                    "Momentum":st.column_config.ProgressColumn(min_value=0,max_value=100,format="%.0f"),
                    "Breadth%":st.column_config.NumberColumn(format="%.0f%%"),
                    "VolRatio":st.column_config.NumberColumn(format="%.2f×")})
            if sel.selection.rows:
                st.session_state.selected_sector=sectors[sel.selection.rows[0]]["name"]; st.rerun()

    # ══════════ RRG ═══════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown('<span style="color:#8b949e;font-size:.78rem">Clockwise: '
            '<span style="color:#3b82f6">Improving</span> → <span style="color:#22c55e">Leading</span> → '
            '<span style="color:#eab308">Weakening</span> → <span style="color:#ef4444">Lagging</span>. '
            'Dashed trails = historical weekly positions (stored in SQLite).</span>',unsafe_allow_html=True)
        rrg_fig=render_rrg(sectors)
        clicked=st.plotly_chart(rrg_fig,use_container_width=True,on_select="rerun",
            selection_mode="points",config={"displayModeBar":False})
        if clicked and getattr(clicked,"selection",None) and clicked.selection.points:
            name=clicked.selection.points[0].get("text","").strip()
            if name: st.session_state.selected_sector=name; st.rerun()
        st.markdown('<hr class="pulse-divider"/>',unsafe_allow_html=True)
        qcols=st.columns(4)
        for col,(q,c,desc) in zip(qcols,[("Leading","#22c55e","High RS · High Momentum"),
                                          ("Improving","#3b82f6","Low RS · Rising Momentum"),
                                          ("Weakening","#eab308","High RS · Falling Momentum"),
                                          ("Lagging","#ef4444","Low RS · Low Momentum")]):
            ns=[s["name"] for s in sectors if s.get("rrg_quadrant")==q]
            col.markdown(f'<div style="background:#0d1117;border:1px solid #21262d;border-top:3px solid {c};'
                f'border-radius:0 0 8px 8px;padding:11px;text-align:center">'
                f'<div style="color:{c};font-weight:700;font-size:.83rem">{q}</div>'
                f'<div style="color:#8b949e;font-size:.67rem;margin:3px 0 7px">{desc}</div>'
                f'<div style="color:{c};font-size:1.5rem;font-weight:800">{len(ns)}</div>'
                f'<div style="color:#8b949e;font-size:.68rem;margin-top:3px">{"  ·  ".join(ns) or "—"}</div>'
                f'</div>',unsafe_allow_html=True)

        # Correlation
        st.markdown('<div class="section-hdr" style="margin-top:14px">30-Day Sector Correlation Matrix</div>',unsafe_allow_html=True)
        st.markdown('<span style="color:#8b949e;font-size:.75rem">Green = positive correlation, Red = negative. '
            'Values near 1.0 = sectors moving together (low diversification benefit).</span>',unsafe_allow_html=True)
        with st.spinner("Computing correlations…"):
            corr=fetch_sector_correlation()
        if corr:
            st.plotly_chart(render_correlation(corr),use_container_width=True,config={"displayModeBar":False})

    # ══════════ SCREENER ══════════════════════════════════════════════════════
    with tabs[2]:
        with st.expander("⚙  Filters",expanded=False):
            fc1,fc2,fc3,fc4=st.columns(4)
            with fc1:
                rsi_min,rsi_max=st.slider("RSI",0,100,(30,75))
                mom_min=st.slider("Min Momentum",0,100,40,step=5)
            with fc2:
                pattern=st.selectbox("Pattern",["all","nr7","nr4","vcp","pocketpivot","rsdiv","minervini"],
                    format_func=lambda x:{"all":"All","nr7":"NR7","nr4":"NR4","vcp":"VCP",
                        "pocketpivot":"Pocket Pivot","rsdiv":"RS Divergence","minervini":"⭐ Minervini"}[x])
                rrg_f=st.selectbox("RRG Quadrant",["all","Leading","Improving","Weakening","Lagging"])
            with fc3:
                dma_f=st.selectbox("DMA Filter",["all","above20","above50","above200","allAbove"],
                    format_func=lambda x:{"all":"All","above20":"Above 20DMA","above50":"Above 50DMA",
                        "above200":"Above 200DMA","allAbove":"All DMAs"}[x])
                vol_bo=st.checkbox("Vol Breakout >1.5×",False)
                mv_only=st.checkbox("Minervini Only",False)
            with fc4:
                sort_by=st.selectbox("Sort By",["change_pct","momentum","rsi","vol_ratio","rs","rs_rank"],
                    format_func=lambda x:{"change_pct":"Change%","momentum":"Momentum","rsi":"RSI",
                        "vol_ratio":"Vol Ratio","rs":"Rel Strength","rs_rank":"RS Rank"}[x])
                grade_f=st.multiselect("Grade",["A","B","C"],default=["A","B","C"])

        active=[f"RSI {rsi_min}–{rsi_max}"]
        if mom_min>0: active.append(f"Mom≥{mom_min}")
        if pattern!="all": active.append(pattern.upper())
        if rrg_f!="all": active.append(rrg_f)
        if dma_f!="all": active.append(dma_f)
        if vol_bo: active.append("VolBreakout")
        if mv_only: active.append("Minervini")
        st.markdown(" ".join(f'<span class="filter-active">{a}</span>' for a in active),unsafe_allow_html=True)

        with st.spinner("Screening full Nifty universe…"):
            results=fetch_screener(rsi_min=rsi_min,rsi_max=rsi_max,momentum_min=mom_min,
                volume_breakout=vol_bo,pattern=pattern,rrg_quadrant=rrg_f,dma_filter=dma_f,
                minervini_only=mv_only)

        if grade_f: results=[r for r in results if r.get("grade","C") in grade_f]
        results=sorted(results,key=lambda s:s.get(sort_by,0) or 0,reverse=True)

        # ── Search box ────────────────────────────────────────────────────────
        search_q = st.text_input("🔍 Search symbol or name",
            placeholder="e.g. RELIANCE or Tata",
            label_visibility="collapsed",
            key="screener_search")
        if search_q:
            q = search_q.upper()
            results = [r for r in results
                       if q in r["symbol"].upper() or q in r.get("name","").upper()]

        a_n=sum(1 for r in results if r.get("grade")=="A")
        b_n=sum(1 for r in results if r.get("grade")=="B")
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin:7px 0 9px">'
            f'<span style="color:#e6edf3;font-weight:700">{len(results)} stocks</span>'
            f'<span class="grade-A">A: {a_n}</span><span class="grade-B">B: {b_n}</span>'
            f'<span class="grade-C">C: {len(results)-a_n-b_n}</span></div>',unsafe_allow_html=True)

        if results:
            rows=[]
            for s in results:
                rsi_val = s["rsi"]
                rows.append({"Grade":s.get("grade","—"),"Symbol":s["symbol"].replace(".NS",""),
                    "Name":s["name"][:22],"Sector":s["sector"],"Price":s["price"],
                    "Chg%":s["change_pct"],
                    "RSI":rsi_val if not math.isnan(rsi_val) else 0,
                    "ATR%":s.get("atr_pct",0),
                    "Mom":s["momentum"],"VolR":s["vol_ratio"],"RS#":s.get("rs_rank",50),
                    "RS%":s["rs"],"RRG":s["rrg_quadrant"],"MV":s.get("minervini_passes",False),
                    "20D":s["above20dma"],"50D":s["above50dma"],"200D":s["above200dma"],
                    "📅":s.get("has_earnings",False),
                    "Signals":" ".join(filter(None,["NR7" if s["is_nr7"] else "",
                        "NR4" if s["is_nr4"] else "","VCP" if s["is_vcp"] else "",
                        "PP" if s["is_pocket_pivot"] else "","RS↑" if s["is_rs_div"] else ""]))or"—"})
            df=pd.DataFrame(rows)

            # CSV Export
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇ Export CSV", csv, "pulse_screener.csv", "text/csv",
                key="screener_csv", help="Download screener results as CSV")

            sel=st.dataframe(df,use_container_width=True,hide_index=True,
                on_select="rerun",selection_mode="single-row",
                column_config={"Grade":st.column_config.TextColumn(width=55),
                    "Price":st.column_config.NumberColumn(format="₹%.2f"),
                    "Chg%":st.column_config.NumberColumn(format="%.2f%%"),
                    "RSI":st.column_config.NumberColumn(format="%.1f"),
                    "ATR%":st.column_config.NumberColumn(format="%.2f%%",help="ATR as % of price — lower = tighter coil"),
                    "Mom":st.column_config.ProgressColumn(min_value=0,max_value=100,format="%.0f"),
                    "VolR":st.column_config.NumberColumn(format="%.2f×"),
                    "RS%":st.column_config.NumberColumn(format="%+.1f%%"),
                    "RS#":st.column_config.NumberColumn(format="%d"),
                    "MV":st.column_config.CheckboxColumn(label="MV",width=35),
                    "20D":st.column_config.CheckboxColumn(width=38),"50D":st.column_config.CheckboxColumn(width=38),
                    "200D":st.column_config.CheckboxColumn(width=38),"📅":st.column_config.CheckboxColumn(width=35)})
            if sel.selection.rows:
                render_stock_detail(results[sel.selection.rows[0]])
        else:
            st.markdown('<div style="text-align:center;padding:40px;color:#8b949e"><div style="font-size:2rem">🔍</div>'
                '<div style="font-weight:600;margin-top:7px">No stocks match</div>'
                '<div style="font-size:.8rem;margin-top:3px">Try relaxing filters</div></div>',unsafe_allow_html=True)

    # ══════════ BREADTH ════════════════════════════════════════════════════════
    with tabs[3]:
        with st.spinner("Computing market breadth…"):
            bdata=fetch_breadth_universe()
        ad,hl,pma=bdata["ad"],bdata["hl"],bdata["pma"]
        from watchlist import get_breadth_history
        history=get_breadth_history(60)

        b1,b2,b3,b4,b5,b6=st.columns(6)
        b1.metric("Advances",ad["advances"])
        b2.metric("Declines",ad["declines"])
        b3.metric("A/D Net",f"{ad['net']:+d}")
        b4.metric("New Highs",hl["new_highs"])
        b5.metric("New Lows",hl["new_lows"])
        b6.metric("H/L Ratio",f"{hl['hl_ratio']:.2f}")
        st.markdown('<hr class="pulse-divider"/>',unsafe_allow_html=True)
        p1,p2,p3=st.columns(3)
        p1.metric("% Above 20 DMA",f"{pma['above_20dma']:.1f}%")
        p2.metric("% Above 50 DMA",f"{pma['above_50dma']:.1f}%")
        p3.metric("% Above 200 DMA",f"{pma['above_200dma']:.1f}%")

        st.markdown('<div class="section-hdr" style="margin-top:10px">Historical Breadth (60 days)</div>',unsafe_allow_html=True)
        render_breadth_charts(history,ad,hl,pma)

        # McClellan approximation
        mcl=ad.get("mclellan_approx",0)
        c="#4ade80" if mcl>0 else "#f87171"
        st.markdown(f'<div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px;margin-top:10px">'
            f'<div style="font-size:.7rem;color:#8b949e;font-weight:700;letter-spacing:.08em">McCLELLAN OSCILLATOR (approx)</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:{c};font-family:\'JetBrains Mono\',monospace">{mcl:+.0f}</div>'
            f'<div style="font-size:.72rem;color:#8b949e;margin-top:3px">'
            f'{"Bullish breadth — most stocks advancing" if mcl>100 else "Bearish breadth — most stocks declining" if mcl<-100 else "Neutral breadth"}'
            f'</div></div>',unsafe_allow_html=True)

    # ══════════ FII/DII ════════════════════════════════════════════════════════
    with tabs[4]:
        with st.spinner("Fetching FII/DII data…"):
            fii_data=fetch_fii_dii()

        is_synthetic=any(r.get("_synthetic") for r in fii_data)
        if is_synthetic:
            st.warning("⚠ NSE FII/DII API unavailable — showing placeholder data. This updates when NSE session is active.",icon="⚠️")

        if fii_data:
            last=fii_data[-1]
            f1,f2,f3,f4=st.columns(4)
            f1.metric("FII Net (latest)",f"₹{last.get('fii_net',0):+,.0f} Cr",
                delta="Buy" if last.get('fii_net',0)>=0 else "Sell")
            f2.metric("DII Net (latest)",f"₹{last.get('dii_net',0):+,.0f} Cr",
                delta="Buy" if last.get('dii_net',0)>=0 else "Sell")
            total_fii=sum(r.get("fii_net",0) for r in fii_data)
            total_dii=sum(r.get("dii_net",0) for r in fii_data)
            f3.metric("FII Cumulative (30d)",f"₹{total_fii:+,.0f} Cr")
            f4.metric("DII Cumulative (30d)",f"₹{total_dii:+,.0f} Cr")
            st.plotly_chart(render_fii_dii(fii_data),use_container_width=True,config={"displayModeBar":False})

            # Table
            st.markdown('<div class="section-hdr">Daily Activity</div>',unsafe_allow_html=True)
            df=pd.DataFrame([{"Date":r["date"],"FII Net (Cr)":r.get("fii_net",0),
                "FII Buy":r.get("fii_buy",0),"FII Sell":r.get("fii_sell",0),
                "DII Net (Cr)":r.get("dii_net",0),"DII Buy":r.get("dii_buy",0),
                "DII Sell":r.get("dii_sell",0)} for r in reversed(fii_data)])
            st.dataframe(df,use_container_width=True,hide_index=True,
                column_config={"FII Net (Cr)":st.column_config.NumberColumn(format="%+,.0f"),
                    "DII Net (Cr)":st.column_config.NumberColumn(format="%+,.0f")})

    # ══════════ WATCHLIST ══════════════════════════════════════════════════════
    with tabs[5]:
        wl=get_watchlist()
        if not wl:
            st.markdown('<div style="text-align:center;padding:40px;color:#8b949e">'
                '<div style="font-size:2rem">⭐</div>'
                '<div style="font-weight:600;margin-top:7px">Watchlist is empty</div>'
                '<div style="font-size:.8rem;margin-top:3px">Click any stock → "Add to Watchlist"</div></div>',
                unsafe_allow_html=True)
        else:
            with st.spinner("Refreshing watchlist…"):
                wl_stocks=fetch_watchlist_stocks()

            for s in wl_stocks or []:
                cc_=pc(s["change_pct"]); sym_=s["symbol"].replace(".NS","")
                b1,b2,b3,b4,b5,b6,b7=st.columns([2,2,1.2,1.2,1.2,1.5,1])
                b1.markdown(f'<div style="font-weight:700;color:#e6edf3;font-family:\'JetBrains Mono\',monospace">{sym_}</div>'
                    f'<div style="font-size:.72rem;color:#8b949e">{s.get("sector","")}</div>',unsafe_allow_html=True)
                b2.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-weight:700">{fi(s["price"])}</div>'
                    f'<div style="font-size:.78rem;color:{cc_};font-weight:700">{fp(s["change_pct"])}</div>',unsafe_allow_html=True)
                b3.markdown(f'<div style="font-size:.7rem;color:#8b949e">RSI</div>'
                    f'<div style="font-weight:700;color:{rsi_gc(s["rsi"])}">{s["rsi"]:.1f}</div>',unsafe_allow_html=True)
                b4.markdown(f'<div style="font-size:.7rem;color:#8b949e">RS#</div>'
                    f'<div style="font-weight:700;color:#e6edf3">{s.get("rs_rank",50)}</div>',unsafe_allow_html=True)
                b5.markdown(f'<div style="font-size:.7rem;color:#8b949e">VolR</div>'
                    f'<div style="font-weight:700;color:{"#4ade80" if s["vol_ratio"]>1.5 else "#e6edf3"}">{s["vol_ratio"]:.2f}×</div>',unsafe_allow_html=True)
                qc_=rrg_c(s.get("rrg_quadrant",""))
                b6.markdown(f'<div style="font-size:.7rem;padding:2px 7px;background:rgba(0,0,0,.3);color:{qc_};border-radius:3px;display:inline-block;margin-top:4px">{s.get("rrg_quadrant","")}</div>',unsafe_allow_html=True)
                with b7:
                    if st.button("✕",key=f"rm_{sym_}",help="Remove"):
                        remove_from_watchlist(s["symbol"]); st.rerun()
                st.markdown('<hr class="pulse-divider"/>',unsafe_allow_html=True)

            # Manual add
            st.markdown('<div class="section-hdr">Add Symbol</div>',unsafe_allow_html=True)
            ca,cb,_=st.columns([2,1,4])
            with ca: add_sym=st.text_input("NSE Symbol",placeholder="e.g. RELIANCE",label_visibility="collapsed")
            with cb:
                if st.button("Add") and add_sym:
                    sym_clean=add_sym.upper().strip()
                    if not sym_clean.endswith(".NS"): sym_clean+=".NS"
                    add_to_watchlist(sym_clean); st.cache_data.clear(); st.rerun()

    # ══════════ ALERTS ═════════════════════════════════════════════════════════
    with tabs[6]:
        alerts=get_all_alerts(100)
        unseen=get_unseen_alerts()
        if unseen:
            st.markdown(f'<div style="background:#1a0e00;border:1px solid #d97706;border-radius:8px;padding:10px 14px;margin-bottom:10px">'
                f'<span style="color:#fde68a;font-weight:700">🔔 {len(unseen)} new alerts since last visit</span></div>',
                unsafe_allow_html=True)
            if st.button("Mark all as seen"): mark_alerts_seen(); st.rerun()

        type_icons={"NR7_SETUP":"🔶","NR4_SETUP":"🔸","POCKET_PIVOT":"🟢","VCP":"🟣",
                    "RS_DIVERGENCE":"🔵","TOP_RS":"⭐","VOL_SURGE":"📊","MINERVINI":"🏆"}
        if alerts:
            for a in alerts:
                icon=type_icons.get(a["alert_type"],"🔔")
                dt=datetime.fromtimestamp(a["fired_at"]).strftime("%d %b %H:%M")
                seen_style="" if a["seen"] else "border-left:3px solid #f0a500;"
                st.markdown(f'<div class="alert-row" style="{seen_style}">'
                    f'<span style="font-size:1.1rem">{icon}</span>'
                    f'<div style="flex:1"><div style="font-size:.82rem;color:#e6edf3;font-weight:600">{a["message"]}</div>'
                    f'<div style="font-size:.7rem;color:#8b949e;margin-top:2px">{dt} · {a["alert_type"]}</div></div>'
                    f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.82rem;color:#8b949e">₹{a["price"]:,.0f}</div>'
                    f'</div>',unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:40px;color:#8b949e">'
                '<div style="font-size:2rem">🔔</div>'
                '<div style="font-weight:600;margin-top:7px">No alerts yet</div>'
                '<div style="font-size:.8rem;margin-top:3px">Alerts fire automatically on each refresh when signals are detected</div></div>',
                unsafe_allow_html=True)

    # Footer
    st.markdown(f'<div style="text-align:center;padding:18px 0 6px;color:#30363d;font-size:.66rem">'
        f'Pulse v3 · Yahoo Finance + NSE India · SQLite persistence · '
        f'Refresh #{st.session_state.refresh_count} · '
        f'Next auto-refresh in {max(0,int(AUTO_REFRESH-(time.time()-st.session_state.last_refresh)))}s'
        f'</div>',unsafe_allow_html=True)

if __name__=="__main__":
    main()
