"""Explanation page - Channel derivation walkthrough."""
import streamlit as st

from core.data_store import load_channel_data
from ui.theme import apply_custom_theme

# Page configuration
st.set_page_config(
    page_title="Explanation - BTC Dashboard",
    page_icon="📚",
    layout="wide",
)

apply_custom_theme()

# Header
st.title("📚 Channel Derivation Explained")
st.markdown("Understanding the Peak/Trough Channel Model")

# Load data for examples
@st.cache_data(ttl=3600)
def load_data():
    return load_channel_data()

channel_data = load_data()

# Introduction
st.markdown(
    """
    ## Overview

    The BTC Dashboard uses a **Peak/Trough Channel Model** to identify historically overvalued
    and undervalued periods in Bitcoin's price history. This page explains the mathematical
    foundation and methodology step by step.
    """
)

st.markdown("---")

# Step 1: Power Law Fair Value
st.markdown("## Step 1: Power Law Fair Value")

st.markdown(
    """
    Bitcoin's long-term price growth follows a **power law** relationship with time since genesis:

    ### Formula
    ```
    Fair Price = C × (days from genesis)^B
    ```

    Where:
    - **Genesis Date**: January 3, 2009 (Bitcoin's first block)
    - **B (exponent)**: 5.93 (empirically fitted to historical data)
    - **C (coefficient)**: Calibrated so the model matches historical mean price/fair ratio

    ### Interpretation
    The fair value represents a "trend line" of Bitcoin's expected price based on network age,
    abstracting away from short-term volatility and market sentiment.
    """
)

if channel_data:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Power Law Exponent (B)", "5.93")
    with col2:
        # Calculate C from recent data
        import numpy as np

        days = (
            (
                __import__("pandas").to_datetime(channel_data.series.date[-1])
                - __import__("pandas").Timestamp("2009-01-03")
            ).days
            + 1
        )
        fair_recent = channel_data.series.fair[-1]
        C = fair_recent / (days**5.93)
        st.metric("Coefficient (C)", f"{C:.8f}")

st.markdown("---")

# Step 2: Ratio Calculation
st.markdown("## Step 2: Price / Fair Ratio")

st.markdown(
    """
    For each day, we calculate the ratio of actual price to fair value:

    ### Formula
    ```
    Ratio = Price / Fair Value
    R_log = log₁₀(Ratio)
    ```

    ### Interpretation
    - **R = 1** (log R = 0): Price equals fair value
    - **R > 1** (log R > 0): Price above fair value (overvalued)
    - **R < 1** (log R < 0): Price below fair value (undervalued)

    Working in log space helps identify peaks and troughs more clearly as they show
    up as symmetric deviations from the baseline.
    """
)

if channel_data:
    col1, col2, col3 = st.columns(3)
    with col1:
        last_ratio_raw = (
            channel_data.series.price[-1] / channel_data.series.fair[-1]
        )
        st.metric("Current Price/Fair", f"{last_ratio_raw:.2f}")
    with col2:
        st.metric("log₁₀(Ratio)", f"{channel_data.series.log10_r[-1]:.3f}")
    with col3:
        # Approximate interpretation
        if last_ratio_raw > 2:
            interpretation = "Overvalued"
        elif last_ratio_raw < 0.5:
            interpretation = "Undervalued"
        else:
            interpretation = "Fair"
        st.metric("Interpretation", interpretation)

st.markdown("---")

# Step 3: Peak Detection
st.markdown("## Step 3: Peak & Trough Detection")

st.markdown(
    """
    Using **scipy.signal.find_peaks**, we identify local maxima (peaks) and minima (troughs)
    in the log ratio time series.

    ### Parameters
    - **Prominence**: 0.28 (minimum height relative to surrounding points)
    - **Distance**: 600 days (minimum spacing between peaks/troughs)
    - **Width**: 5 days (minimum width of peak/trough)

    ### Purpose
    These parameters are tuned to identify major market cycle tops and bottoms while filtering
    out noise and minor fluctuations.

    Historically, Bitcoin has experienced:
    - **Peaks**: 2011, 2013 (Nov), 2017 (Dec), 2021 (Apr & Nov)
    - **Troughs**: 2011, 2015, 2018-2019, 2022

    ### Trough Detection
    Troughs are found by inverting the signal and detecting peaks in `-log₁₀(R)`.
    """
)

st.info(
    """
    **Why log space?**

    Log transformation makes multiplicative changes additive:
    - 10x increase and 10x decrease have equal magnitude in log space
    - Peaks and troughs become symmetric around the fair value line
    - Makes linear regression more appropriate
    """
)

st.markdown("---")

# Step 4: Linear Regression
st.markdown("## Step 4: Channel Lines (Linear Regression)")

st.markdown(
    """
    Once peaks and troughs are identified, we fit **linear regression lines** to each set:

    ### Peak Line
    ```
    log₁₀(Peak R) = m_peak × days + b_peak
    ```

    ### Trough Line
    ```
    log₁₀(Trough R) = m_trough × days + b_trough
    ```

    These lines define the **upper bound** (peak line) and **lower bound** (trough line)
    of the channel.

    ### Converting back to price
    ```
    Peak Price = Fair Value × 10^(log₁₀(Peak R))
    Trough Price = Fair Value × 10^(log₁₀(Trough R))
    ```

    ### Projection to 2030
    The regression lines are extrapolated forward to December 31, 2030, providing a
    forward-looking channel for guidance.
    """
)

st.warning(
    """
    **Important**: Extrapolation assumes the historical relationship continues. This is a model,
    not a guarantee. Bitcoin's market dynamics may change over time.
    """
)

st.markdown("---")

# Step 5: Ratio Indicator
st.markdown("## Step 5: Channel Position (0-100%)")

st.markdown(
    """
    Finally, we normalize the current price position within the channel to a 0-100% scale:

    ### Formula
    ```
    Position (%) = ((Price - Trough Price) / (Peak Price - Trough Price)) × 100
    Position = clamp(Position, 0, 100)
    ```

    ### Interpretation
    - **0%**: Price at trough line (historically the bottom of cycles)
    - **50%**: Price at fair value (midpoint between peak and trough)
    - **100%**: Price at peak line (historically the top of cycles)

    ### Usage
    This ratio serves as the primary input to the rebalancing strategy:
    - **Below threshold** (e.g., < 46%): Maintain high BTC exposure (accumulation zone)
    - **Above threshold** (e.g., ≥ 46%): Gradually reduce BTC exposure (distribution zone)
    """
)

if channel_data:
    current_position = channel_data.last_ratio

    st.markdown(f"### Current Channel Position: **{current_position:.1f}%**")

    # Visual representation
    progress_bar_color = (
        "🟢"
        if current_position < 30
        else "🟡" if current_position < 70 else "🔴"
    )

    st.progress(min(int(current_position), 100) / 100)

    if current_position < 30:
        st.success("**Accumulation Zone** - Historically near cycle bottoms")
    elif current_position < 70:
        st.info("**Neutral Zone** - Between extremes")
    else:
        st.warning("**Distribution Zone** - Historically near cycle tops")

st.markdown("---")

# Summary
st.markdown("## Summary: Data Pipeline")

st.markdown(
    """
    ```mermaid
    graph TD
        A[CoinCodex API] --> B[Daily BTC Prices]
        B --> C[Power Law Fair Value]
        C --> D[Price / Fair Ratio]
        D --> E[Peak Detection]
        D --> F[Trough Detection]
        E --> G[Linear Regression: Peak Line]
        F --> H[Linear Regression: Trough Line]
        G --> I[Channel Boundaries]
        H --> I
        I --> J[Normalize to 0-100%]
        J --> K[Strategy Input]
    ```

    ### Key Outputs
    1. **btc.json**: Contains all historical and extended data
    2. **Channel Position**: 0-100% indicator for current price location
    3. **Peak/Trough Projections**: Forward-looking channel boundaries
    4. **Fair Value Line**: Long-term power-law trend

    ### Update Frequency
    - **Historical Data**: Daily (via CoinCodex API)
    - **Live Prices**: Real-time (via Binance WebSocket)
    - **Channel Calculation**: Daily (via `update.py` script)
    """
)

# References
with st.expander("📚 References & Further Reading"):
    st.markdown(
        """
        ### Academic & Research Papers
        - **Power Laws in Economics**: Early research on scaling relationships
        - **Bitcoin's Power Law**: Community-driven analysis of BTC price vs time

        ### Technical Resources
        - **scipy.signal.find_peaks**: [SciPy Documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html)
        - **Linear Regression**: [scikit-learn LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html)

        ### Data Sources
        - **CoinCodex**: Historical Bitcoin price data
        - **Binance**: Real-time WebSocket price feed (BTCUSDT)
        - **Coinbase**: Fallback REST API (BTC-USD)

        ### Community Resources
        - **Bitcoin Talk Forums**: Early discussions on cycle patterns
        - **Woo Charts**: Alternative indicators and on-chain metrics
        - **Glassnode**: On-chain analytics and market intelligence

        ### Important Disclaimers
        - This model is for educational purposes
        - Past performance does not guarantee future results
        - Not financial advice - do your own research
        - Bitcoin is a highly volatile asset - invest responsibly
        """
    )

# Interactive exploration
if channel_data:
    st.markdown("---")
    st.markdown("## Interactive Exploration")

    selected_date_idx = st.slider(
        "Select a historical date",
        min_value=0,
        max_value=len(channel_data.series.date) - 1,
        value=len(channel_data.series.date) - 1,
    )

    selected_date = channel_data.series.date[selected_date_idx]
    selected_price = channel_data.series.price[selected_date_idx]
    selected_fair = channel_data.series.fair[selected_date_idx]
    selected_ratio_pct = channel_data.series.ratio[selected_date_idx]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Date", selected_date)

    with col2:
        st.metric("Price", f"${selected_price:,.0f}")

    with col3:
        st.metric("Fair Value", f"${selected_fair:,.0f}")

    with col4:
        st.metric("Position", f"{selected_ratio_pct:.1f}%")

    # Interpretation for selected date
    if selected_ratio_pct < 30:
        st.success(f"On {selected_date}, BTC was in the **accumulation zone** ({selected_ratio_pct:.1f}%)")
    elif selected_ratio_pct > 70:
        st.warning(f"On {selected_date}, BTC was in the **distribution zone** ({selected_ratio_pct:.1f}%)")
    else:
        st.info(f"On {selected_date}, BTC was in the **neutral zone** ({selected_ratio_pct:.1f}%)")
