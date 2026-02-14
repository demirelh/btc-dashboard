"""Strategy page - Configure and visualize rebalancing strategy."""
import streamlit as st
from datetime import date

from core.data_store import load_channel_data
from core.models import StrategyParams
from core.strategy import StrategyEngine
from ui.theme import apply_custom_theme
from ui.components import plot_exposure_curve, plot_ratio_distribution
from core.utils import format_number, format_usd

# Page configuration
st.set_page_config(
    page_title="Strategy - BTC Dashboard",
    page_icon="⚙️",
    layout="wide",
)

apply_custom_theme()

# Header
st.title("⚙️ Rebalancing Strategy")
st.markdown("Configure and visualize your BTC rebalancing strategy")

# Load data
@st.cache_data(ttl=3600)
def load_data():
    return load_channel_data()

channel_data = load_data()

if not channel_data:
    st.error("No channel data found. Please run the data update first.")
    st.stop()

# Sidebar controls
st.sidebar.markdown("## Strategy Configuration")

# Sell-Leiter (Ladder)
ladder = st.sidebar.selectbox(
    "Sell Ladder",
    options=["g0", "g1", "g2"],
    index=1,
    format_func=lambda x: {
        "g0": "g0 (Soft: 1 - x²)",
        "g1": "g1 (Linear: 1 - x)",
        "g2": "g2 (Aggressive: (1 - x)²)",
    }[x],
    help="Shape of the sell curve as ratio increases",
)

# Parameters
st.sidebar.markdown("### Thresholds")

sell_start = st.sidebar.slider(
    "Sell Start (%)",
    min_value=0.0,
    max_value=100.0,
    value=46.0,
    step=1.0,
    help="Ratio threshold to start selling BTC",
)

buy_threshold = st.sidebar.slider(
    "Buy Threshold (%)",
    min_value=0.0,
    max_value=100.0,
    value=14.0,
    step=1.0,
    help="Ratio threshold for re-entry in 'wait' mode",
)

# Re-entry mode
reentry_mode = st.sidebar.selectbox(
    "Re-Entry Mode",
    options=["instant", "wait", "gradual"],
    index=0,
    format_func=lambda x: {
        "instant": "Instant (immediately 100%)",
        "wait": "Wait (only @ Buy Threshold)",
        "gradual": "Gradual (smooth increase)",
    }[x],
    help="How to re-enter when ratio drops below Sell Start",
)

# Start parameters
st.sidebar.markdown("### Backtest Settings")

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
    help="Initial BTC exposure",
)

# Create strategy params
params = StrategyParams(
    ladder=ladder,
    sell_start=sell_start,
    buy_threshold=buy_threshold,
    reentry_mode=reentry_mode,
    start_weight=start_weight / 100.0,
    start_date=str(start_date),
)

# Main content
st.markdown("## Current Strategy Configuration")

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        f"""
        **Ladder**: {ladder.upper()}

        **Sell Start**: {sell_start:.0f}%

        **Re-Entry**: {reentry_mode.title()}
        """
    )

with col2:
    # Get current recommendation
    current_ratio = channel_data.last_ratio
    current_weight = StrategyEngine.sell_weight(current_ratio, sell_start, ladder)

    if current_ratio < sell_start:
        if reentry_mode == "instant":
            current_weight = 1.0
        elif reentry_mode == "wait":
            current_weight = 1.0 if current_ratio <= buy_threshold else current_weight

    action_tag = "BUY" if current_weight > 0.8 else ("SELL" if current_weight < 0.5 else "HOLD")

    st.metric(
        "Current Position",
        f"{current_ratio:.1f}%",
        delta=f"Ratio in channel",
    )

with col3:
    st.metric(
        "Target Exposure",
        f"{current_weight * 100:.1f}% BTC",
        delta=action_tag,
    )

# Ladder hints
hints = StrategyEngine.get_ladder_hints(sell_start, ladder)
st.caption(
    f"Ladder weights @ 50%={hints['w50']:.1f}%, 70%={hints['w70']:.1f}%, 90%={hints['w90']:.1f}%"
)

st.markdown("---")

# Exposure curve
st.markdown("## Exposure vs Ratio Curve")
st.markdown("Shows target BTC exposure as a function of channel position")

# Generate curve data
ratios = list(range(0, 101))
weights = []
for r in ratios:
    w = StrategyEngine.sell_weight(r, sell_start, ladder)
    if r < sell_start:
        if reentry_mode == "instant":
            w = 1.0
        elif reentry_mode == "wait" and r > buy_threshold:
            w = 0.5  # Approximate hold zone
    weights.append(w * 100)

exposure_fig = plot_exposure_curve(
    ratios, weights, sell_start, current_ratio, current_weight * 100
)
st.plotly_chart(exposure_fig, use_container_width=True)

st.markdown("---")

# Ratio distribution
st.markdown("## Historical Ratio Distribution")
st.markdown(f"Distribution of channel positions since {start_date}")

# Get data slice
dates = channel_data.series.date
start_idx = next((i for i, d in enumerate(dates) if d >= str(start_date)), 0)
ratios_slice = channel_data.series.ratio[start_idx:]

if len(ratios_slice) > 1:
    dist_fig = plot_ratio_distribution(
        ratios_slice, current_ratio, str(start_date)
    )
    st.plotly_chart(dist_fig, use_container_width=True)
else:
    st.warning("Not enough data for distribution analysis")

# Strategy explanation
with st.expander("📖 Strategy Explanation"):
    st.markdown(
        f"""
        ### How This Strategy Works

        #### Sell Regime (Ratio ≥ {sell_start:.0f}%)
        When the channel position exceeds {sell_start:.0f}%, the strategy begins reducing BTC exposure
        according to the selected ladder:

        - **g0 (Soft)**: 1 - x² — Maintains higher exposure longer (concave curve)
        - **g1 (Linear)**: 1 - x — Proportional reduction (balanced)
        - **g2 (Aggressive)**: (1 - x)² — Rapid exposure reduction (convex curve)

        where x is the normalized position within the sell range: x = (ratio - {sell_start:.0f}) / (100 - {sell_start:.0f})

        **Important**: In the sell regime, the strategy only *reduces* exposure, never increases it
        (sell-only hysteresis to avoid buying at peaks).

        #### Re-Entry (Ratio < {sell_start:.0f}%)
        When ratio drops below {sell_start:.0f}%, the re-entry mode determines behavior:

        - **Instant** ({reentry_mode == "instant" and "✓" or ""}): Immediately return to 100% BTC
        - **Wait** ({reentry_mode == "wait" and "✓" or ""}): Only return to 100% when ratio ≤ {buy_threshold:.0f}%
        - **Gradual** ({reentry_mode == "gradual" and "✓" or ""}): Smooth increase as ratio falls

        #### Rationale
        This strategy aims to:
        1. **Sell high**: Reduce exposure as BTC approaches historically overvalued levels
        2. **Buy low**: Accumulate when BTC returns to historically undervalued levels
        3. **Avoid timing**: Use systematic rules instead of discretionary decisions
        4. **Reduce volatility**: Hold stablecoins/cash during euphoric phases
        """
    )

# Next triggers
st.markdown("## Next Trigger Points")

col1, col2 = st.columns(2)

with col1:
    if current_ratio < sell_start:
        sell_price = (
            channel_data.last_trough
            + (sell_start / 100.0) * (channel_data.last_peak - channel_data.last_trough)
        )
        st.success(
            f"""
            **Next SELL Trigger**

            Begins @ Ratio {sell_start:.0f}%

            Estimated price: {format_usd(sell_price)}
            (based on current channel)
            """
        )
    else:
        next_ratio = min(current_ratio + 1, 100)
        next_price = (
            channel_data.last_trough
            + (next_ratio / 100.0) * (channel_data.last_peak - channel_data.last_trough)
        )
        st.warning(
            f"""
            **Further Reduction**

            @ Ratio {next_ratio:.0f}%

            Estimated price: {format_usd(next_price)}
            """
        )

with col2:
    if reentry_mode == "wait":
        buy_price = (
            channel_data.last_trough
            + (buy_threshold / 100.0)
            * (channel_data.last_peak - channel_data.last_trough)
        )
        st.info(
            f"""
            **Re-Entry Trigger**

            100% BTC @ Ratio {buy_threshold:.0f}%

            Estimated price: {format_usd(buy_price)}
            (wait mode active)
            """
        )
    elif reentry_mode == "instant":
        st.info(
            f"""
            **Re-Entry Trigger**

            100% BTC immediately

            When ratio < {sell_start:.0f}%
            (instant mode active)
            """
        )
    else:
        st.info(
            f"""
            **Re-Entry Behavior**

            Gradual increase

            Smooth ramp-up as ratio falls
            below {sell_start:.0f}%
            """
        )
