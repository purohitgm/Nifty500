import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import time


# Page config
st.set_page_config(page_title="Pro Asset Comparison Dashboard", layout="wide", page_icon="📈")


# ========== CUSTOM CSS & THEMEING ==========
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stMetric > label {color: #1f77b4; font-size: 1.1em; font-weight: 600;}
    .stMetric > div > div {font-size: 2em; font-weight: bold;}
    [data-testid="stSidebar"] {background-color: #ffffff;}
    .metric-card {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                  margin: 0.5rem 0;}
    .metric-title {color: white; margin: 0 0 0.5rem 0; font-size: 1.1em;}
    .metric-value {font-size: 2em; color: white; font-weight: bold; margin: 0.25rem 0;}
    .metric-change {font-weight: bold; margin-top: 0.25rem;}
</style>
""", unsafe_allow_html=True)


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
    "Silver": "SI=F"
}


# Multi-asset selector
selected_assets = st.sidebar.multiselect(
    "📊 Select Assets", 
    list(tickers.keys()), 
    default=list(tickers.keys()),
    help="Choose 1-5 assets for comparison (max performance)"
)


if len(selected_assets) > 5:
    st.sidebar.warning("⚠️ Limited to 5 assets for optimal performance")
    selected_assets = selected_assets[:5]


# Date/Period controls
period = st.sidebar.selectbox("📅 Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"], index=3)
start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input("End Date", datetime.now())


# Correlation timeframe
corr_tf = st.sidebar.selectbox(
    "🔗 Correlation Timeframe", 
    ["daily", "weekly", "monthly", "3_months", "yearly", "5_yearly"],
    index=0
)


# Refresh controls
st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
if col1.button("🔄 Refresh Data", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.success("✅ Data refreshed successfully!")
    st.rerun()


auto_refresh = col2.checkbox("🔄 Auto-refresh (60s)")


st.sidebar.markdown("---")
st.sidebar.caption("💾 Data cached 5min for performance")


# ========== DATA LOADING ==========
selected_ticker_symbols = {k: v for k, v in tickers.items() if k in selected_assets}


@st.cache_data(ttl=300) # 5 minute cache
def load_data(symbols, period, start, end):
    """Load adjusted close prices from Yahoo Finance"""
    if not symbols:
        return pd.DataFrame()
    
    try:
        data = yf.download(
            list(symbols.values()), 
            period=period, 
            start=start, 
            end=end, 
            group_by='ticker',
            progress=False
        )["Adj Close"]
        data.columns = list(symbols.keys())
        return data.dropna()
    except Exception as e:
        st.error(f"Data fetch error: {e}")
        return pd.DataFrame()


data = load_data(selected_ticker_symbols, period, start_date, end_date)


if data.empty or data.shape[1] == 0:
    st.error("❌ No data available. Please check:")
    st.markdown("- ✅ Selected assets")
    st.markdown("- ✅ Date range (markets closed on weekends)")
    st.markdown("- ✅ Internet connection")
    st.stop()


# Auto-refresh
if auto_refresh:
    time.sleep(60)
    st.rerun()


# ========== ENHANCED KPI METRICS ==========
st.header(f"📊 Live Metrics ({len(selected_assets)} Assets)")
metric_container = st.container()
with metric_container:
    metric_cols = st.columns(min(len(selected_assets), 5))
    for i, asset in enumerate(selected_assets):
        col_idx = i % 5
        with metric_cols[col_idx]:
            try:
                current = data[asset].iloc[-1]
                prev = data[asset].iloc[-2] if len(data) > 1 else current
                start_val = data[asset].iloc[0]
                
                total_return = ((current / start_val - 1) * 100)
                daily_change = ((current / prev - 1) * 100)
                
                change_color = "#00ff88" if total_return >= 0 else "#ff4444"
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">{asset}</div>
                    <div class="metric-value">{current:.2f}</div>
                    <div class="metric-change" style="color: {change_color}">
                        {total_return:+.1f}% (Total)
                    </div>
                    <div style="color: {'#00ff88' if daily_change >= 0 else '#ff4444'}; font-size: 0.85em;">
                        {daily_change:+.2f}% (Daily)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except:
                st.metric(asset, "N/A")


# ========== TABS LAYOUT ==========
tab1, tab2, tab3 = st.tabs(["📈 Price Action", "🔗 Correlations", "📋 Analytics & Risk"])


with tab1:
    st.subheader("Normalized Performance Comparison")
    st.caption("All assets start at 100 for fair comparison")
    
    norm_data = (data / data.iloc[0]) * 100
    
    fig_price = go.Figure()
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F7DC6F', '#BB8FCE']
    
    for i, (asset, col) in enumerate(norm_data.items()):
        fig_price.add_trace(go.Scatter(
            x=norm_data.index, y=col, name=asset,
            line=dict(color=colors[i], width=3),
            hovertemplate=f'<b>{asset}</b><br>Date: %{{x}}<br>Value: %{{y:.1f}}<extra></extra>'
        ))
    
    fig_price.update_layout(
        title="Asset Performance (Normalized to 100)",
        xaxis_title="Date",
        yaxis_title="Normalized Price Index (100 = Start)",
        hovermode='x unified',
        template='plotly_white',
        height=550,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_price, use_container_width=True)


with tab2:
    st.subheader(f"🔗 {corr_tf.replace('_', ' ').title()} Returns Correlation Matrix")
    
    def resample_returns(df, timeframe):
        """Resample returns for correlation analysis"""
        pct_returns = df.pct_change().dropna()
        resample_rules = {
            "daily": None,
            "weekly": 'W',
            "monthly": 'M', 
            "3_months": '3M',
            "yearly": 'Y',
            "5_yearly": '5Y'
        }
        rule = resample_rules.get(timeframe)
        if rule is None:
            return pct_returns
        return pct_returns.resample(rule).apply(lambda x: (1 + x).prod() - 1).dropna()
    
    resampled_returns = resample_returns(data, corr_tf)
    if resampled_returns.empty:
        st.warning("⚠️ Insufficient data for this timeframe")
    else:
        corr_matrix = resampled_returns.corr()
        
        # Heatmap
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=list(corr_matrix.columns),
            y=list(corr_matrix.index),
            colorscale='RdBu_r',
            zmid=0, zmin=-1, zmax=1,
            hoverongaps=False,
            colorbar=dict(title="Correlation Coefficient")
        ))
        fig_corr.update_layout(
            title=f"{corr_tf.replace('_', ' ').title()} Period Correlation Heatmap",
            xaxis_title="Assets", yaxis_title="Assets",
            height=500,
            font=dict(size=12)
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Correlation table
        st.subheader("Correlation Values Table")
        corr_styled = corr_matrix.round(3).style\
            .background_gradient(cmap='RdBu_r', axis=1)\
            .format("{:.3f}")
        st.dataframe(corr_styled, use_container_width=True)


with tab3:
    st.subheader("📊 Performance Summary & Risk Metrics")
    
    # Calculate metrics
    total_returns = ((data.iloc[-1] / data.iloc[0] - 1) * 100)
    daily_vol = data.pct_change().std() * np.sqrt(252) * 100 # Annualized
    drawdowns = ((data / data.cummax()) - 1) * 100
    max_dd = drawdowns.min()
    
    metrics_df = pd.DataFrame({
        'Total Return (%)': total_returns.round(2),
        'Ann. Volatility (%)': daily_vol.round(2),
        'Max Drawdown (%)': max_dd.round(2)
    })
    
    st.dataframe(
        metrics_df.style.format("{:.2f}").background_gradient(cmap='RdYlGn'),
        use_container_width=True
    )
    st.caption("*Annualized volatility assumes 252 trading days")


# ========== DOWNLOAD SECTION ==========
with st.sidebar.expander("📥 Downloads"):
    # Raw price data
    csv_price = data.to_csv()
    st.download_button(
        "💾 Price Data (CSV)",
        csv_price,
        "asset_prices.csv",
        "text/csv"
    )
    
    # Correlation data
    resampled_returns = resample_returns(data, corr_tf)
    if not resampled_returns.empty:
        csv_corr = resampled_returns.to_csv()
        st.download_button(
            f"🔗 {corr_tf} Returns (CSV)",
            csv_corr,
            f"{corr_tf}_returns.csv",
            "text/csv"
        )
    
    # Metrics summary
    metrics_csv = metrics_df.to_csv()
    st.download_button(
        "📊 Summary Metrics (CSV)",
        metrics_csv,
        "performance_metrics.csv",
        "text/csv"
    )


# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Built with ❤️ using Streamlit + yfinance + Plotly | Data: Yahoo Finance
</div>
""", unsafe_allow_html=True)