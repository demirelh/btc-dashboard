"""Backtest page - Compare strategy vs HODL."""
import streamlit as st
from datetime import date

from core.data_store import load_channel_data
from core.models import StrategyParams
from core.backtest import BacktestEngine
from ui.theme import apply_custom_theme
from ui.components import plot_backtest_results
from core.utils import format_pct

# Page configuration
st.set_page_config(
    page_title="Backtest - BTC Dashboard",
    page_icon="📈",
    layout="wide",
)

apply_custom_theme()

# Header
st.title("📈 Strategy Backtest")
st.markdown("Compare strategy performance vs simple HODL")

# Load data
@st.cache_data(ttl=3600)
def load_data():
    return load_channel_data()

channel_data = load_data()

if not channel_data:
    st.error("No channel data found. Please run the data update first.")
    st.stop()

# Sidebar controls (same as strategy page)
st.sidebar.markdown("## Backtest Configuration")

ladder = st.sidebar.selectbox(
    "Sell Ladder",
    options=["g0", "g1", "g2"],
    index=1,
    format_func=lambda x: {
        "g0": "g0 (Soft: 1 - x²)",
        "g1": "g1 (Linear: 1 - x)",
        "g2": "g2 (Aggressive: (1 - x)²)",
    }[x],
)

sell_start = st.sidebar.slider(
    "Sell Start (%)",
    min_value=0.0,
    max_value=100.0,
    value=46.0,
    step=1.0,
)

buy_threshold = st.sidebar.slider(
    "Buy Threshold (%)",
    min_value=0.0,
    max_value=100.0,
    value=14.0,
    step=1.0,
)

reentry_mode = st.sidebar.selectbox(
    "Re-Entry Mode",
    options=["instant", "wait", "gradual"],
    index=0,
    format_func=lambda x: {
        "instant": "Instant",
        "wait": "Wait",
        "gradual": "Gradual",
    }[x],
)

start_date = st.sidebar.date_input(
    "Start Date",
    value=date(2018, 1, 1),
    min_value=date(2013, 1, 1),
    max_value=date.today(),
)

start_weight = st.sidebar.slider(
    "Start Weight (%)",
    min_value=0.0,
    max_value=100.0,
    value=100.0,
    step=5.0,
)

# Create params
params = StrategyParams(
    ladder=ladder,
    sell_start=sell_start,
    buy_threshold=buy_threshold,
    reentry_mode=reentry_mode,
    start_weight=start_weight / 100.0,
    start_date=str(start_date),
)

# Run backtest
@st.cache_data(ttl=300, show_spinner="Running backtest...")
def run_backtest(params_dict):
    """Run backtest with caching."""
    params = StrategyParams(**params_dict)
    dates = channel_data.series.date
    prices = channel_data.series.price
    ratios = channel_data.series.ratio

    start_idx = next((i for i, d in enumerate(dates) if d >= params.start_date), 0)

    if start_idx >= len(dates) - 1:
        return None

    return BacktestEngine.run_backtest(
        dates, prices, ratios, params, start_idx
    )

# Convert params to dict for caching
params_dict = {
    "ladder": params.ladder,
    "sell_start": params.sell_start,
    "buy_threshold": params.buy_threshold,
    "reentry_mode": params.reentry_mode,
    "start_weight": params.start_weight,
    "start_date": params.start_date,
}

result = run_backtest(params_dict)

if not result:
    st.error("Not enough data for backtest with selected start date.")
    st.stop()

# Performance metrics
st.markdown("## Performance Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Strategy Return",
        format_pct(result.strategy_return),
        delta=f"vs HODL: {format_pct(result.performance_delta)}",
    )

with col2:
    st.metric(
        "HODL Return",
        format_pct(result.hodl_return),
    )

with col3:
    st.metric(
        "Strategy Max DD",
        format_pct(result.strategy_max_drawdown),
    )

with col4:
    st.metric(
        "HODL Max DD",
        format_pct(result.hodl_max_drawdown),
    )

# Performance comparison
st.markdown("---")

if result.strategy_return > result.hodl_return:
    st.success(
        f"✅ **Strategy outperformed HODL by {format_pct(result.performance_delta)}**"
    )
elif result.strategy_return < result.hodl_return:
    st.warning(
        f"⚠️ **Strategy underperformed HODL by {format_pct(result.performance_delta)}**"
    )
else:
    st.info("➡️ **Strategy matched HODL performance**")

# Equity curve chart
st.markdown("## Equity Curves & Exposure")
st.markdown(
    f"Backtest period: {result.dates[0]} to {result.dates[-1]} ({len(result.dates)} days)"
)

backtest_fig = plot_backtest_results(result)
st.plotly_chart(backtest_fig, width="stretch")

# Last trade info
if result.last_trade:
    st.markdown("## Last Strategy Change")
    st.info(
        f"""
        **Date**: {result.last_trade['date']}

        **Action**: {result.last_trade['action']}

        **Ratio**: {result.last_trade['ratio']:.1f}%

        **New Weight**: {result.last_trade['weight'] * 100:.1f}% BTC
        """
    )
else:
    st.info("No rebalancing occurred during the backtest period")

# Analysis
with st.expander("📊 Detailed Analysis"):
    st.markdown(
        """
        ### Backtest Methodology

        This backtest simulates a simple rebalancing strategy:

        1. **Daily Rebalancing**: Portfolio is rebalanced at each day's closing price
        2. **Two Assets**: BTC and cash/stablecoins (assumed 0% return)
        3. **No Fees**: Transaction costs are not included (conservative assumption)
        4. **No Slippage**: Trades execute at closing price
        5. **Perfect Execution**: No implementation lag

        ### Performance Metrics

        - **Total Return**: Cumulative return from start to end
        - **Max Drawdown**: Largest peak-to-trough decline
        - **Relative Performance**: Strategy return minus HODL return

        ### Interpretation

        **Outperformance** suggests the strategy successfully:
        - Sold during overvalued periods
        - Re-entered during undervalued periods
        - Reduced volatility exposure

        **Underperformance** may indicate:
        - Bull market throughout period (HODL wins in uptrends)
        - Thresholds too conservative/aggressive
        - Missing major rallies due to early sells

        ### Important Notes

        - Past performance ≠ future results
        - Real trading involves fees, slippage, taxes
        - Psychological factors (fear, greed) affect execution
        - Channel projections are not guarantees
        - Consider this as one tool in a broader strategy
        """
    )

# Configuration summary
st.markdown("---")
st.markdown("## Backtest Configuration")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f"""
        **Strategy Parameters**
        - Ladder: {ladder.upper()}
        - Sell Start: {sell_start:.0f}%
        - Buy Threshold: {buy_threshold:.0f}%
        - Re-Entry Mode: {reentry_mode.title()}
        """
    )

with col2:
    st.markdown(
        f"""
        **Backtest Settings**
        - Start Date: {start_date}
        - Start Weight: {start_weight:.0f}% BTC
        - Days: {len(result.dates)}
        - Rebalancing: Daily
        """
    )
