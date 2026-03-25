import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import time

# Page config
st.set_page_config(page_title="Pro Asset Comparison Dashboard", layout="wide", page_icon="📈")

# ========== CUSTOM CSS ==========
st.markdown("""
<style>
.main {background-color: #f8f9fa;}
.stMetric > label {color: #1f77b4; font-size: 1.1em; font-weight: 600;}
.stMetric > div > div {font-size: 2em; font-weight: bold;}
[data-testid="stSidebar"] {background-color: #ffffff;}
.metric-card {
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
border-radius: 12px; padding: 1.5rem;
box-shadow: 0 4px 12px rgba(0,0,0,0.1);
margin: 0.5rem 0;
}
.metric-title {color: white;}
.metric-value {font-size: 2em; color: white; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# Title
st.title("📈 Pro Asset Comparison Dashboard")

# ========== SIDEBAR ==========
st.sidebar.header("⚙️ Dashboard Controls")

tickers = {
"Nifty 50": "^NSEI",
"Crude Oil": "CL=F",
"Gold": "GC=F",
"Bitcoin": "BTC-USD",
"Silver": "SI=F"
}

selected_assets = st.sidebar.multiselect(
"Select Assets",
list(tickers.keys()),
default=list(tickers.keys())
)

if len(selected_assets) > 5:
st.sidebar.warning("Max 5 assets allowed")
selected_assets = selected_assets[:5]

period = st.sidebar.selectbox("Period", ["1mo","3mo","6mo","1y","2y","5y"], index=3)

# ========== DATA ==========
@st.cache_data(ttl=300)
def load_data(symbols, period):
if not symbols:
return pd.DataFrame()

try:
raw = yf.download(
list(symbols.values()),
period=period,
progress=False
)

# FIX: handle single vs multi ticker
if len(symbols) == 1:
df = raw["Adj Close"].to_frame()
df.columns = list(symbols.keys())
else:
df = raw["Adj Close"]
df.columns = list(symbols.keys())

return df.dropna()

except Exception as e:
st.error(f"Error fetching data: {e}")
return pd.DataFrame()

selected_ticker_symbols = {k: v for k, v in tickers.items() if k in selected_assets}
data = load_data(selected_ticker_symbols, period)

if data.empty:
st.error("No data available")
st.stop()

# ========== METRICS ==========
st.header("📊 Metrics")

cols = st.columns(len(selected_assets))

for i, asset in enumerate(selected_assets):
with cols[i]:
if asset in data.columns and len(data) > 1:
current = data[asset].iloc[-1]
prev = data[asset].iloc[-2]
start = data[asset].iloc[0]

total_return = (current / start - 1) * 100
daily = (current / prev - 1) * 100

st.metric(
asset,
f"{current:.2f}",
f"{daily:.2f}%"
)
else:
st.metric(asset, "N/A")

# ========== PRICE CHART ==========
st.subheader("📈 Normalized Performance")

norm = (data / data.iloc[0]) * 100

fig = go.Figure()

for col in norm.columns:
fig.add_trace(go.Scatter(
x=norm.index,
y=norm[col],
name=col
))

st.plotly_chart(fig, use_container_width=True)

# ========== CORRELATION ==========
st.subheader("🔗 Correlation")

returns = data.pct_change().dropna()

if not returns.empty:
corr = returns.corr()

fig_corr = go.Figure(data=go.Heatmap(
z=corr.values,
x=corr.columns,
y=corr.columns,
colorscale="RdBu",
zmin=-1,
zmax=1
))

st.plotly_chart(fig_corr, use_container_width=True)
st.dataframe(corr)
else:
st.warning("Not enough data for correlation")

# ========== RISK ==========
st.subheader("📋 Risk Metrics")

returns = data.pct_change().dropna()

vol = returns.std() * np.sqrt(252) * 100
dd = (data / data.cummax() - 1) * 100

metrics = pd.DataFrame({
"Return %": ((data.iloc[-1] / data.iloc[0] - 1) * 100),
"Volatility %": vol,
"Max Drawdown %": dd.min()
})

st.dataframe(metrics)

# ========== FOOTER ==========
st.markdown("---")
st.caption("Built with Streamlit + yfinance")