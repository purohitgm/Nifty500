"""
╔══════════════════════════════════════════════════════════════╗
║  NIFTY MARKET INTELLIGENCE — Streamlit Edition              ║
║  Stack: Streamlit + yfinance + Plotly + pandas-ta            ║
╠══════════════════════════════════════════════════════════════╣
║  SETUP:                                                      ║
║    pip install streamlit yfinance plotly pandas pandas-ta    ║
║                   streamlit-autorefresh streamlit-extras     ║
║    streamlit run streamlit_app.py                            ║
║                                                              ║
║  DEPLOY:                                                     ║
║    streamlit run streamlit_app.py --server.port 8501         ║
║    # Or deploy free at share.streamlit.io                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ── AUTO-REFRESH ──────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, key="live_refresh")  # refresh every 60s
except ImportError:
    st.warning("Install streamlit-autorefresh for live updates: pip install streamlit-autorefresh")

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'IBM Plex Mono', monospace !important; }
  .main { background: #080d14; }
  .stApp { background: #080d14; }
  .block-container { padding: 1rem 2rem !important; }
  .metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 14px 18px;
  }
  .grade-a { color: #00e5a0; font-weight: 700; }
  .grade-b { color: #fbbf24; font-weight: 700; }
  .grade-c { color: #f87171; font-weight: 700; }
  div[data-testid="metric-container"] > label { font-size: 11px !important; color: #6b7280 !important; }
  div[data-testid="metric-container"] > div { font-size: 22px !important; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────
INDICES = {
    "NIFTY 50":   "^NSEI",
    "NIFTY 100":  "^CNX100",
    "NIFTY 200":  "^CNX200",
    "NIFTY 500":  "^CNX500",
    "SENSEX":     "^BSESN",
    "INDIA VIX":  "^INDIAVIX",
}

SECTOR_INDICES = {
    "Nifty Bank":        "^NSEBANK",
    "Nifty IT":          "^CNXIT",
    "Nifty Auto":        "^CNXAUTO",
    "Nifty Pharma":      "^CNXPHARMA",
    "Nifty FMCG":        "^CNXFMCG",
    "Nifty Metal":       "^CNXMETAL",
    "Nifty Realty":      "^CNXREALTY",
    "Nifty Energy":      "^CNXENERGY",
    "Nifty Infra":       "^CNXINFRA",
    "Nifty Fin Services":"^CNXFINANCE",
    "Nifty Healthcare":  "^CNXHEALTH",
    "Nifty PSU Bank":    "^CNXPSUBANK",
    "Nifty Oil & Gas":   "^CNXOILGAS",
    "Nifty Media":       "^CNXMEDIA",
    "Nifty Cons Dur":    "^CNXCONSDURBL",
}

NIFTY50_STOCKS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
    "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
    "LT.NS","BAJFINANCE.NS","ASIANPAINT.NS","MARUTI.NS","TITAN.NS",
    "WIPRO.NS","HCLTECH.NS","ULTRACEMCO.NS","AXISBANK.NS","NESTLEIND.NS",
    "SUNPHARMA.NS","TATAMOTORS.NS","TATASTEEL.NS","TECHM.NS","INDUSINDBK.NS",
    "BAJAJFINSV.NS","POWERGRID.NS","NTPC.NS","ONGC.NS","COALINDIA.NS",
    "ADANIGREEN.NS","ADANIPORTS.NS","HINDALCO.NS","GRASIM.NS","DIVISLAB.NS",
    "CIPLA.NS","DRREDDY.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS",
    "BPCL.NS","IOC.NS","JSWSTEEL.NS","VEDL.NS","APOLLOHOSP.NS",
    "M&M.NS","TVSMOTOR.NS","PERSISTENT.NS","ZOMATO.NS","PIDILITIND.NS",
]

COLORS = {
    "bull": "#00e5a0", "bear": "#f87171", "neutral": "#fbbf24",
    "bg": "#080d14", "card": "#0d1520", "border": "#1e293b",
    "muted": "#6b7280", "text": "#e2e8f0",
}

# ── TECHNICAL INDICATORS ──────────────────────────────────────
def calc_rsi(series: pd.Series, period: int = 14) -> float:
    """Wilder RSI"""
    delta = series.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2) if not rsi.empty else None

def calc_sma(series: pd.Series, period: int) -> float | None:
    if len(series) < period: return None
    return round(float(series.rolling(period).mean().iloc[-1]), 2)

def calc_ema(series: pd.Series, period: int) -> float | None:
    if len(series) < period: return None
    return round(float(series.ewm(span=period, adjust=False).mean().iloc[-1]), 2)

def is_nr7(highs: pd.Series, lows: pd.Series) -> bool:
    """Narrowest range in 7 days"""
    if len(highs) < 7: return False
    ranges = (highs - lows).iloc[-7:]
    return float(ranges.iloc[-1]) == float(ranges.min())

def is_vcp(closes: pd.Series, highs: pd.Series, lows: pd.Series) -> bool:
    """Simplified Volatility Contraction Pattern"""
    if len(closes) < 20: return False
    vols = []
    for w in range(4):
        s = closes.iloc[-(20 - w*5): -(15 - w*5) or None]
        if len(s) < 3: continue
        vols.append((s.max() - s.min()) / s.mean())
    return all(vols[i] <= vols[i-1] for i in range(1, len(vols))) if len(vols) >= 3 else False

def is_pocket_pivot(volumes: pd.Series, closes: pd.Series) -> bool:
    """Volume > max up-day volume in prior 10 sessions"""
    if len(volumes) < 11: return False
    today_up = closes.iloc[-1] > closes.iloc[-2]
    if not today_up: return False
    prev_10 = pd.DataFrame({'v': volumes.iloc[-11:-1], 'c': closes.iloc[-11:-1], 'cp': closes.iloc[-12:-2].values})
    up_vols = prev_10[prev_10['c'] > prev_10['cp']]['v']
    return float(volumes.iloc[-1]) > float(up_vols.max()) if len(up_vols) > 0 else False

def momentum_score(rsi, vol_ratio, abv50, nr7, pp, rs_change) -> float:
    return round(
        max(0, min(100, ((rsi - 40) / 30) * 100)) * 0.20 +
        min(100, vol_ratio * 50)                   * 0.20 +
        (75 if abv50 else 25)                      * 0.15 +
        (85 if nr7  else 30)                       * 0.10 +
        (82 if pp   else 28)                       * 0.15 +
        max(0, min(100, 50 + rs_change * 5))       * 0.20,
    1)

def assign_grade(score, rsi, rs_change) -> str:
    if score > 68 and 50 <= rsi <= 75 and rs_change > 0: return "A"
    if score > 50 and rs_change > -2: return "B"
    return "C"

# ── DATA LOADERS (cached 60s) ─────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_indices() -> pd.DataFrame:
    rows = []
    for name, ticker in INDICES.items():
        try:
            q = yf.Ticker(ticker).fast_info
            rows.append({
                "Index": name, "Level": round(q.last_price or 0, 2),
                "Change%": round(q.three_month_return or 0, 2),
            })
        except Exception:
            pass
    return pd.DataFrame(rows)

@st.cache_data(ttl=60, show_spinner=False)
def load_sectors() -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=180)
    nifty = yf.download("^NSEI", start=start, end=end, progress=False)["Close"].squeeze()

    rows = []
    for name, ticker in SECTOR_INDICES.items():
        try:
            hist = yf.download(ticker, start=start, end=end, progress=False)
            if hist.empty: continue
            c = hist["Close"].squeeze()
            h = hist["High"].squeeze()
            l = hist["Low"].squeeze()
            v = hist.get("Volume", pd.Series(dtype=float)).squeeze()

            rsi   = calc_rsi(c)
            sma20 = calc_sma(c, 20)
            price = float(c.iloc[-1])

            # RS vs Nifty 20-day
            if len(c) >= 20 and len(nifty) >= 20:
                sec_ret   = (float(c.iloc[-1])    - float(c.iloc[-20]))    / float(c.iloc[-20])
                nifty_ret = (float(nifty.iloc[-1]) - float(nifty.iloc[-20])) / float(nifty.iloc[-20])
                rs = round((sec_ret - nifty_ret) * 100, 2)
            else:
                rs = 0.0

            vol_ratio = 1.0
            if len(v) > 20 and v.sum() > 0:
                avg20 = float(v.iloc[-20:].mean())
                vol_ratio = round(float(v.iloc[-1]) / avg20, 2) if avg20 > 0 else 1.0

            breadth = round(min(95, max(10, 50 + rs * 3)), 1)
            score   = momentum_score(rsi or 50, vol_ratio, sma20 and price > sma20,
                                     is_nr7(h, l), False, rs)
            chg = round((price / float(c.iloc[-2]) - 1) * 100, 2) if len(c) > 1 else 0

            rows.append({
                "Sector": name, "Ticker": ticker,
                "Level": round(price, 2), "Change%": chg,
                "RSI(14)": rsi, "Vol/20DMA": vol_ratio,
                "RS vs N50": rs, "Breadth%": breadth,
                "Momentum": score,
            })
        except Exception as e:
            st.warning(f"Could not load {name}: {e}")

    df = pd.DataFrame(rows).sort_values("Momentum", ascending=False)
    return df

@st.cache_data(ttl=120, show_spinner=False)
def load_stocks(symbols: list[str]) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=180)
    nifty = yf.download("^NSEI", start=start, end=end, progress=False)["Close"].squeeze()

    rows = []
    for sym in symbols:
        try:
            hist = yf.download(sym, start=start, end=end, progress=False)
            if len(hist) < 30: continue

            c = hist["Close"].squeeze()
            h = hist["High"].squeeze()
            l = hist["Low"].squeeze()
            v = hist.get("Volume", pd.Series(dtype=float)).squeeze()

            rsi    = calc_rsi(c)
            sma20  = calc_sma(c, 20)
            ema20  = calc_ema(c, 20)
            sma50  = calc_sma(c, 50)
            sma200 = calc_sma(c, 200)
            price  = float(c.iloc[-1])
            prev   = float(c.iloc[-2])
            chg    = round((price / prev - 1) * 100, 2)

            avg20v    = float(v.iloc[-20:].mean()) if len(v) > 20 and v.sum() > 0 else 1
            vol_ratio = round(float(v.iloc[-1]) / avg20v, 2) if avg20v > 0 else 1.0

            if len(c) >= 20 and len(nifty) >= 20:
                rs = round(((price - float(c.iloc[-20])) / float(c.iloc[-20]) -
                            (float(nifty.iloc[-1]) - float(nifty.iloc[-20])) / float(nifty.iloc[-20])) * 100, 2)
            else:
                rs = 0.0

            nr7 = is_nr7(h, l)
            vcp = is_vcp(c, h, l)
            pp  = is_pocket_pivot(v, c)

            score = momentum_score(rsi or 50, vol_ratio,
                                   sma50 is not None and price > sma50,
                                   nr7, pp, rs)
            grade = assign_grade(score, rsi or 50, rs)

            try:
                info  = yf.Ticker(sym).fast_info
                mcap  = round((info.market_cap or 0) / 1e10, 1)
            except Exception:
                mcap = None

            rows.append({
                "Symbol": sym.replace(".NS",""),
                "Price": round(price, 2), "Change%": chg,
                "RSI": rsi, "Vol/DMA": vol_ratio,
                "MCap(₹Bn)": mcap,
                "20EMA": ema20, "50SMA": sma50, "200SMA": sma200,
                ">20EMA": ema20 is not None and price > ema20,
                ">50SMA": sma50 is not None and price > sma50,
                ">200SMA": sma200 is not None and price > sma200,
                "NR7": nr7, "VCP": vcp, "PP": pp,
                "RS vs N50": rs,
                "Momentum": score, "Grade": grade,
            })
        except Exception:
            continue

    return pd.DataFrame(rows).sort_values("Momentum", ascending=False)

# ── PLOTLY HELPERS ────────────────────────────────────────────
PLOT_LAYOUT = dict(
    plot_bgcolor="#080d14", paper_bgcolor="#080d14",
    font=dict(family="IBM Plex Mono", color="#9ca3af", size=10),
    margin=dict(l=40, r=10, t=30, b=30),
    xaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
    yaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e293b"),
)

def make_heatmap(df: pd.DataFrame) -> go.Figure:
    df_s = df.sort_values("Change%")
    colors = [("#f87171" if c < -1.5 else "#f97316" if c < -0.3 else
               "#6b7280" if c < 0.3 else "#4ade80" if c < 1.5 else "#00e5a0")
              for c in df_s["Change%"]]
    fig = go.Figure(go.Bar(
        x=df_s["Change%"], y=df_s["Sector"],
        orientation="h", marker_color=colors,
        text=[f"{c:+.2f}%" for c in df_s["Change%"]],
        textposition="outside", textfont=dict(size=10),
    ))
    fig.update_layout(**PLOT_LAYOUT, title="Sector % Change Today",
                      height=420, xaxis_title="Change %")
    return fig

def make_momentum_chart(df: pd.DataFrame) -> go.Figure:
    df_s = df.sort_values("Momentum")
    colors = [("#f87171" if m < 40 else "#fbbf24" if m < 58 else "#4ade80" if m < 72 else "#00e5a0")
              for m in df_s["Momentum"]]
    fig = go.Figure(go.Bar(
        x=df_s["Momentum"], y=df_s["Sector"],
        orientation="h", marker_color=colors,
        text=[str(m) for m in df_s["Momentum"]],
        textposition="outside", textfont=dict(size=10),
    ))
    fig.update_layout(**PLOT_LAYOUT, title="Sector Momentum Score (0–100)",
                      height=420, xaxis=dict(**PLOT_LAYOUT["xaxis"], range=[0, 105]))
    return fig

def make_treemap(df: pd.DataFrame) -> go.Figure:
    fig = px.treemap(
        df, path=["Sector"], values=df["Momentum"].abs() + 10,
        color="Change%", color_continuous_scale=["#f87171", "#6b7280", "#00e5a0"],
        color_continuous_midpoint=0,
        hover_data={"RSI(14)": True, "Momentum": True},
    )
    fig.update_layout(**PLOT_LAYOUT, title="Industry Heatmap", height=380, margin=dict(l=0, r=0, t=30, b=0))
    fig.update_traces(textfont=dict(family="IBM Plex Mono", size=12, color="white"))
    return fig

def make_rs_scatter(df_stocks: pd.DataFrame) -> go.Figure:
    if df_stocks.empty: return go.Figure()
    df_s = df_stocks.dropna(subset=["RSI", "RS vs N50"])
    colors = [("#00e5a0" if g == "A" else "#fbbf24" if g == "B" else "#f87171") for g in df_s["Grade"]]
    fig = go.Figure(go.Scatter(
        x=df_s["RSI"], y=df_s["RS vs N50"],
        mode="markers+text", text=df_s["Symbol"],
        textposition="top center", textfont=dict(size=8),
        marker=dict(color=colors, size=8, opacity=0.8),
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="#374151")
    fig.add_hline(y=0,  line_dash="dash", line_color="#374151")
    fig.update_layout(**PLOT_LAYOUT, title="RSI vs Relative Strength (Grade colored)",
                      xaxis_title="RSI(14)", yaxis_title="RS vs Nifty 50 (%)", height=380)
    return fig

# ── MAIN APP ──────────────────────────────────────────────────
def main():
    # ── HEADER ────────────────────────────────────────────────
    col_logo, col_title, col_time = st.columns([1, 8, 2])
    with col_logo:
        st.markdown('<div style="font-size:32px;margin-top:4px">📊</div>', unsafe_allow_html=True)
    with col_title:
        st.markdown("""
        <h1 style="font-family:'IBM Plex Mono',monospace;font-size:22px;color:#00e5a0;margin:0;letter-spacing:0.12em">
          NIFTY MARKET INTELLIGENCE
        </h1>
        <p style="font-size:10px;color:#6b7280;margin:0;letter-spacing:0.08em">
          QUANTITATIVE SECTOR & STOCK ANALYTICS · LIVE DATA VIA YFINANCE
        </p>
        """, unsafe_allow_html=True)
    with col_time:
        st.markdown(f'<p style="font-size:10px;color:#6b7280;text-align:right;margin-top:8px">'
                    f'Updated: {datetime.now().strftime("%H:%M:%S")}</p>', unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1e293b;margin:8px 0">', unsafe_allow_html=True)

    # ── SIDEBAR FILTERS ────────────────────────────────────────
    st.sidebar.markdown("### 🔧 Filters")
    min_momentum = st.sidebar.slider("Min Momentum Score", 0, 90, 0, 5)
    rsi_range    = st.sidebar.slider("RSI Range",          20, 85, (30, 80), 5)
    grade_filter = st.sidebar.multiselect("Grade Filter", ["A", "B", "C"], default=["A", "B", "C"])
    only_nr7     = st.sidebar.checkbox("NR7 Only")
    only_vcp     = st.sidebar.checkbox("VCP Only")
    only_pp      = st.sidebar.checkbox("Pocket Pivot Only")
    only_abv50   = st.sidebar.checkbox("Above 50 SMA Only")
    only_vol     = st.sidebar.checkbox("Volume Surge (>1.3x)")
    num_stocks   = st.sidebar.slider("# Stocks to Load", 10, 50, 25, 5)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Grading Logic:**")
    st.sidebar.markdown("🏆 **A**: RS>0 + Mom>68 + RSI 50–75")
    st.sidebar.markdown("📊 **B**: RS>-2 + Mom>50")
    st.sidebar.markdown("⚠️ **C**: Weak sector or stock")

    # ── TABS ──────────────────────────────────────────────────
    tab_ov, tab_sec, tab_stocks, tab_grades = st.tabs([
        "📈 Overview", "🗂️ Sectors", "📋 Stocks", "🏆 AI Grades"
    ])

    # ═══════════════════════════════════════════════════════════
    # OVERVIEW TAB
    # ═══════════════════════════════════════════════════════════
    with tab_ov:
        with st.spinner("Fetching live index data…"):
            idx_df = load_indices()

        if not idx_df.empty:
            cols = st.columns(len(idx_df))
            for i, row in idx_df.iterrows():
                chg = row["Change%"]
                color = COLORS["bull"] if chg >= 0 else COLORS["bear"]
                with cols[i]:
                    st.metric(
                        label=row["Index"],
                        value=f"{row['Level']:,.2f}",
                        delta=f"{chg:+.2f}%"
                    )
        st.markdown("---")

        with st.spinner("Loading sector data…"):
            sec_df = load_sectors()

        if not sec_df.empty:
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(make_heatmap(sec_df), use_container_width=True)
            with c2: st.plotly_chart(make_momentum_chart(sec_df), use_container_width=True)
            st.plotly_chart(make_treemap(sec_df), use_container_width=True)

    # ═══════════════════════════════════════════════════════════
    # SECTORS TAB
    # ═══════════════════════════════════════════════════════════
    with tab_sec:
        with st.spinner("Loading sectors…"):
            sec_df = load_sectors()

        if sec_df.empty:
            st.error("Could not load sector data.")
        else:
            # Summary metrics
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a: st.metric("Top Sector",   sec_df.iloc[0]["Sector"], f'{sec_df.iloc[0]["Change%"]:+.2f}%')
            with col_b: st.metric("Avg Momentum", round(sec_df["Momentum"].mean(), 1))
            with col_c: st.metric("Sectors > 0%", int((sec_df["Change%"] > 0).sum()))
            with col_d: st.metric("Avg RSI",       round(sec_df["RSI(14)"].dropna().mean(), 1))

            # Styled table
            def color_change(val):
                color = "#00e5a0" if val > 0 else "#f87171"
                return f"color: {color}; font-weight: bold"
            def color_rsi(val):
                if val is None: return ""
                if val >= 70: return "color: #f97316"
                if val >= 55: return "color: #00e5a0"
                if val <= 35: return "color: #a78bfa"
                return "color: #fbbf24"
            def color_score(val):
                c = "#00e5a0" if val >= 72 else "#4ade80" if val >= 58 else "#fbbf24" if val >= 44 else "#f87171"
                return f"color: {c}; font-weight: bold"

            styled = (sec_df.style
                      .applymap(color_change, subset=["Change%", "RS vs N50"])
                      .applymap(color_rsi,    subset=["RSI(14)"])
                      .applymap(color_score,  subset=["Momentum"])
                      .format({"Level": "{:,.0f}", "Change%": "{:+.2f}%",
                               "RSI(14)": "{:.1f}", "Vol/20DMA": "{:.2f}x",
                               "RS vs N50": "{:+.2f}%", "Breadth%": "{:.1f}%",
                               "Momentum": "{:.1f}"})
                      .set_properties(**{"font-family": "IBM Plex Mono", "font-size": "11px"})
            )
            st.dataframe(styled, use_container_width=True, height=480)

    # ═══════════════════════════════════════════════════════════
    # STOCKS TAB
    # ═══════════════════════════════════════════════════════════
    with tab_stocks:
        with st.spinner(f"Fetching {num_stocks} stocks with live technicals…"):
            stocks_df = load_stocks(NIFTY50_STOCKS[:num_stocks])

        if stocks_df.empty:
            st.warning("No stock data loaded.")
        else:
            # Apply sidebar filters
            mask = (
                (stocks_df["Momentum"] >= min_momentum) &
                (stocks_df["RSI"].fillna(50).between(rsi_range[0], rsi_range[1])) &
                (stocks_df["Grade"].isin(grade_filter))
            )
            if only_nr7:   mask &= stocks_df["NR7"]
            if only_vcp:   mask &= stocks_df["VCP"]
            if only_pp:    mask &= stocks_df["PP"]
            if only_abv50: mask &= stocks_df[">50SMA"]
            if only_vol:   mask &= stocks_df["Vol/DMA"] > 1.3
            filtered = stocks_df[mask]

            st.caption(f"Showing {len(filtered)} / {len(stocks_df)} stocks after filters")

            # Charts
            c1, c2 = st.columns(2)
            with c1:
                fig_sc = make_rs_scatter(filtered)
                st.plotly_chart(fig_sc, use_container_width=True)
            with c2:
                # Momentum distribution histogram
                fig_hist = go.Figure(go.Histogram(
                    x=filtered["Momentum"], nbinsx=20,
                    marker_color="#00e5a0", opacity=0.7,
                ))
                fig_hist.update_layout(**PLOT_LAYOUT, title="Momentum Score Distribution",
                                       xaxis_title="Score", yaxis_title="Count", height=380)
                st.plotly_chart(fig_hist, use_container_width=True)

            # Table
            display_cols = ["Symbol","Price","Change%","RSI","Vol/DMA","RS vs N50",
                            ">50SMA","NR7","VCP","PP","Momentum","Grade"]
            def color_grade(val):
                return {"A": "color: #00e5a0; font-weight: bold",
                        "B": "color: #fbbf24; font-weight: bold",
                        "C": "color: #f87171; font-weight: bold"}.get(val, "")
            styled = (filtered[display_cols].style
                      .applymap(color_change,  subset=["Change%","RS vs N50"])
                      .applymap(color_rsi,     subset=["RSI"])
                      .applymap(color_score,   subset=["Momentum"])
                      .applymap(color_grade,   subset=["Grade"])
                      .format({"Price": "₹{:,.0f}", "Change%": "{:+.2f}%",
                               "RSI": "{:.1f}", "Vol/DMA": "{:.2f}x",
                               "RS vs N50": "{:+.2f}%", "Momentum": "{:.1f}"})
                      .set_properties(**{"font-family": "IBM Plex Mono", "font-size": "11px"})
            )
            st.dataframe(styled, use_container_width=True, height=500)

    # ═══════════════════════════════════════════════════════════
    # AI GRADES TAB
    # ═══════════════════════════════════════════════════════════
    with tab_grades:
        with st.spinner("Computing AI grades…"):
            stocks_df = load_stocks(NIFTY50_STOCKS[:num_stocks])

        if stocks_df.empty:
            st.warning("Load stocks first.")
        else:
            grade_a = stocks_df[stocks_df["Grade"] == "A"].head(16)
            grade_b = stocks_df[stocks_df["Grade"] == "B"].head(12)
            grade_c = stocks_df[stocks_df["Grade"] == "C"].head(8)

            # Summary
            ca, cb, cc, cd = st.columns(4)
            with ca: st.metric("🏆 Grade A", len(grade_a), "Prime candidates")
            with cb: st.metric("📊 Grade B", len(grade_b), "Watchlist")
            with cc: st.metric("⚠️ Grade C", len(grade_c), "Avoid")
            with cd: st.metric("Avg Score", round(stocks_df["Momentum"].mean(), 1))

            # Pie chart
            grade_counts = stocks_df["Grade"].value_counts()
            fig_pie = go.Figure(go.Pie(
                labels=grade_counts.index, values=grade_counts.values,
                marker_colors=["#00e5a0", "#fbbf24", "#f87171"],
                hole=0.55, textfont=dict(family="IBM Plex Mono", size=12),
            ))
            fig_pie.update_layout(**PLOT_LAYOUT, title="Grade Distribution", height=280)
            st.plotly_chart(fig_pie, use_container_width=True)

            # Grade A
            if not grade_a.empty:
                st.markdown("### 🏆 Grade A — Prime Buy Candidates")
                cols = st.columns(min(4, len(grade_a)))
                for i, (_, row) in enumerate(grade_a.iterrows()):
                    with cols[i % 4]:
                        chg_c = COLORS["bull"] if row["Change%"] >= 0 else COLORS["bear"]
                        tags  = " ".join([t for t, v in [("NR7", row["NR7"]), ("VCP", row["VCP"]), ("PP", row["PP"]), ("50D", row[">50SMA"])] if v])
                        st.markdown(f"""
                        <div style="background:rgba(0,229,160,0.06);border:1px solid rgba(0,229,160,0.2);
                                    border-radius:10px;padding:12px;margin-bottom:8px">
                          <div style="font-weight:700;color:#f1f5f9;font-size:13px">{row["Symbol"]}</div>
                          <div style="color:{chg_c};font-size:11px">{row["Change%"]:+.2f}%</div>
                          <div style="color:#9ca3af;font-size:10px">RSI {row["RSI"]:.1f} · {row["Momentum"]:.1f} score</div>
                          <div style="color:#6b7280;font-size:10px">{tags}</div>
                        </div>""", unsafe_allow_html=True)

            # Grading rules
            st.markdown("---")
            st.markdown("### Grading Criteria")
            cr, cc2, cp = st.columns(3)
            for col, g, color, rules in [
                (cr, "A", "#00e5a0", ["Sector RS > 0 vs Nifty", "Momentum score > 68", "RSI 50–75", "Volume > 1.2x DMA", "≥1 pattern (NR7/VCP/PP)"]),
                (cc2,"B", "#fbbf24", ["Sector RS > -2",          "Momentum score > 50", "RSI 45–78", "Volume neutral+",    "No pattern required"]),
                (cp, "C", "#f87171", ["Sector RS < -2",           "Momentum score < 50", "RSI < 45",  "Vol below DMA",     "Avoid fresh longs"]),
            ]:
                with col:
                    rules_html = "".join(f'<li style="color:#9ca3af;font-size:11px">{r}</li>' for r in rules)
                    st.markdown(f"""
                    <div style="background:{color}0d;border:1px solid {color}33;border-radius:10px;padding:14px">
                      <div style="color:{color};font-size:16px;font-weight:900;margin-bottom:8px">Grade {g}</div>
                      <ul style="padding-left:16px">{rules_html}</ul>
                    </div>""", unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1e293b;margin-top:32px">',unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;color:#374151;text-align:center">'
                'Nifty Market Intelligence · Data via Yahoo Finance · Not financial advice</p>',
                unsafe_allow_html=True)

if __name__ == "__main__":
    main()
