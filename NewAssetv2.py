import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import time

# Page config
st.set_page_config(
page_title="Pro Asset Comparison Dashboard",
layout="wide",
page_icon="📈"
)

# ========== CUSTOM CSS & THEME ==========
st.markdown(
"""
<style>
.main {background-color: #f8f9fa;}
[data-testid="stSidebar"] {background-color: #ffffff;}
.metric-card {
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
border-radius: 12px;
padding: 1.5rem;
box-shadow: 0 4px 12px rgba(0,0,0,0.1);
margin: 0.5rem 0;
}
.metric-title {
color: white;
margin: 0 0 0.5rem 0;
font-size: 1.1em;
}
.metric-value {
font-size: 2em;
color: white;
font-weight: bold;
margin: 0.25rem 0;
}
.metric-change {
font-weight: bold;
margin-top: 0.25rem;
}
</style>
""",
unsafe_allow_html=True,
)

# Title
st.title("📈 Pro Asset Comparison Dashboard")
st.markdown("**Live Yahoo Finance Data** | Professional Trading Analytics | Updated Mar 2026")

# ========== SIDEBAR CONTROLS ==========
st.sidebar.header("⚙️ Dashboard Controls")
st.sidebar.markdown("---")

# Asset tickers dictionary
tickers = {
"Nifty 50": "^NSEI",
"Crude Oil": "CL=F",
"Gold": "GC=F",
"Bitcoin": "BTC-USD",
"Silver": "SI=F",
}

# Multi-asset selector
selected_assets = st.sidebar.multiselect(
"📊 Select Assets",
list(tickers.keys()),
default=list(tickers.keys()),
help="Choose 1-5 assets for comparison (max performance)",
)

if len(selected_assets) > 5:
st.sidebar.warning("Max 5 assets allowed")
selected_assets = selected_assets[:5]

# Date/Period controls
period = st.sidebar.selectbox(
"📅 Period",
["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"],
index=3,
)
start_date = st.sidebar.date_input(
"Start Date",
datetime.now() - timedelta(days=365),
)
end_date = st.sidebar.date_input("End Date", datetime.now())

# Correlation timeframe
corr_tf = st.sidebar.selectbox(
"🔗 Correlation Timeframe",
["daily", "weekly", "monthly", "3_months", "yearly", "5_yearly"],
index=0,
)

# EMA options for correlation
st.sidebar.markdown("### 📐 Correlation Basis")
corr_basis = st.sidebar.radio(
"Use for correlation:",
["Price Returns", "EMA 5 Returns", "EMA 13 Returns", "EMA 21 Returns"],
index=0,
)

# Refresh controls
st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
if col1.button("🔄 Refresh Data", type="primary", use_container_width=True):
st.cache_data.clear()
st.success("✅ Data refreshed successfully!")
st.experimental_rerun()

auto_refresh = col2.checkbox("🔄 Auto-refresh (60s)")

st.sidebar.markdown("---")
st.sidebar.caption("💾 Data cached 5min for performance")

# ========== DATA LOADING ==========
selected_ticker_symbols = {k: v for k, v in tickers.items() if k in selected_assets}


@st.cache_data(ttl=300)
def load_data(symbols, period, start, end):
"""Load adjusted close prices from Yahoo Finance."""
if not symbols:
return pd.DataFrame()

try:
data = yf.download(
list(symbols.values()),
period=period,
start=start,
end=end,
group_by="ticker",
progress=False,
)["Adj Close"]
data.columns = list(symbols.keys())
return data.dropna()
except Exception as e:
st.error(f"Data fetch error: {e}")
return pd.DataFrame()


data = load_data(selected_ticker_symbols, period, start_date, end_date)

if data.empty or data.shape[1] == 0:
st.error("❌ No data available. Please check:")
st.markdown("- Selected assets")
st.markdown("- Date range (markets closed on weekends)")
st.markdown("- Internet connection")
st.stop()

# Auto-refresh
if auto_refresh:
time.sleep(60)
st.experimental_rerun()

# ========== ENHANCED KPI METRICS ==========
st.header(f"📊 Live Metrics ({len(selected_assets)} Assets)")
metric_container = st.container()
with metric_container:
metric_cols = st.columns(min(len(selected_assets), 5))
for i, asset in enumerate(selected_assets):
col_idx = i % len(metric_cols)
with metric_cols[col_idx]:
try:
current = data[asset].iloc[-1]
prev = data[asset].iloc[-2] if len(data) > 1 else current
start_val = data[asset].iloc[0]

total_return = (current / start_val - 1) * 100
daily_change = (current / prev - 1) * 100

change_color = "#00ff88" if total_return >= 0 else "#ff4444"
daily_color = "#00ff88" if daily_change >= 0 else "#ff4444"

st.markdown(
f"""
<div class="metric-card">
<div class="metric-title">{asset}</div>
<div class="metric-value">{current:.2f}</div>
<div class="metric-change" style="color: {change_color}">
{total_return:+.1f}% (Total)
</div>
<div style="color: {daily_color}; font-size: 0.85em;">
{daily_change:+.2f}% (Daily)
</div>
</div>
""",
unsafe_allow_html=True,
)
except Exception:
st.metric(asset, "N/A")

# ========== TABS LAYOUT ==========
tab1, tab2, tab3 = st.tabs(
["📈 Price Action", "🔗 Correlations", "📋 Analytics & Risk"]
)

with tab1:
st.subheader("Normalized Performance Comparison")
st.caption("All assets start at 100 for fair comparison")

norm_data = (data / data.iloc[0]) * 100

fig_price = go.Figure()
colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#F7DC6F", "#BB8FCE"]

for i, (asset, col) in enumerate(norm_data.items()):
fig_price.add_trace(
go.Scatter(
x=norm_data.index,
y=col,
name=asset,
line=dict(color=colors[i % len(colors)], width=3),
hovertemplate=(
f"<b>{asset}</b><br>Date: %{{x}}"
"<br>Value: %{y:.1f}<extra></extra>"
),
)
)

fig_price.update_layout(
title="Asset Performance (Normalized to 100)",
xaxis_title="Date",
yaxis_title="Normalized Price Index (100 = Start)",
hovermode="x unified",
template="plotly_white",
height=550,
legend=dict(
orientation="h",
yanchor="bottom",
y=1.02,
xanchor="right",
x=1,
),
)
st.plotly_chart(fig_price, use_container_width=True)


def resample_returns(returns_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
"""Resample returns for correlation analysis."""
resample_rules = {
"daily": None,
"weekly": "W",
"monthly": "M",
"3_months": "3M",
"yearly": "Y",
"5_yearly": "5Y",
}
rule = resample_rules.get(timeframe)
if rule is None:
return returns_df.dropna()
return (
returns_df.resample(rule)
.apply(lambda x: (1 + x).prod() - 1)
.dropna()
)


def ema_returns(price_df: pd.DataFrame, period: int) -> pd.DataFrame:
"""Compute log returns of EMA(period) for each column."""
ema = price_df.ewm(span=period, adjust=False).mean()
ema_ret = np.log(ema / ema.shift(1)).dropna()
return ema_ret


with tab2:
basis_label = {
"Price Returns": "Price",
"EMA 5 Returns": "EMA 5",
"EMA 13 Returns": "EMA 13",
"EMA 21 Returns": "EMA 21",
}[corr_basis]

st.subheader(
f"🔗 {corr_tf.replace('_', ' ').title()} Correlation Matrix ({basis_label})"
)

# Base returns depending on basis
if corr_basis == "Price Returns":
base_returns = data.pct_change().dropna()
elif corr_basis == "EMA 5 Returns":
base_returns = ema_returns(data, 5)
elif corr_basis == "EMA 13 Returns":
base_returns = ema_returns(data, 13)
else:
base_returns = ema_returns(data, 21)

resampled_returns = resample_returns(base_returns, corr_tf)

if resampled_returns.empty:
st.warning("⚠️ Insufficient data for this EMA/timeframe combination")
else:
corr_matrix = resampled_returns.corr()

fig_corr = go.Figure(
data=go.Heatmap(
z=corr_matrix.values,
x=list(corr_matrix.columns),
y=list(corr_matrix.index),
colorscale="RdBu_r",
zmid=0,
zmin=-1,
zmax=1,
hoverongaps=False,
colorbar=dict(title="Correlation Coefficien