"""Dashboard page - Live KPIs and main channel chart."""
import streamlit as st
import time

from core.data_store import load_channel_data
from core.price_feed import get_price_feed
from ui.theme import apply_custom_theme
from ui.components import render_kpi_cards, plot_channel_chart, plot_ratio_chart

# Page configuration
st.set_page_config(
    page_title="Dashboard - BTC Dashboard",
    page_icon="₿",
    layout="wide",
)

apply_custom_theme()

# Header
st.title("₿ BTC Dashboard")
st.markdown("Real-time view of Bitcoin price channel and key metrics")

# Load data
@st.cache_data(ttl=3600, show_spinner="Loading channel data...")
def load_data():
    """Load channel data with caching."""
    return load_channel_data()

channel_data = load_data()

if not channel_data:
    st.error(
        """
        **No channel data found.**

        Please run the data update script first:
        ```bash
        python update.py
        ```
        Or use the update function:
        ```python
        from core.data_store import update_channel_data
        update_channel_data()
        ```
        """
    )
    st.stop()

# Get live price (non-cached, updated in real-time)
price_feed = get_price_feed()
live_price = price_feed.get_latest_price()

# Render KPI cards
st.markdown("### Key Performance Indicators")
render_kpi_cards(channel_data, live_price)

st.markdown("---")

# Main channel chart
st.markdown("### Price Channel Analysis")
st.markdown(
    "Historical Bitcoin price with power-law fair value, peak line, and trough line projections"
)

fig = plot_channel_chart(channel_data)
st.plotly_chart(fig, use_container_width=True)

# Ratio indicator
st.markdown("### Channel Position Indicator")
st.markdown(
    "Shows where BTC is positioned within the channel (0% = trough line, 100% = peak line)"
)

ratio_fig = plot_ratio_chart(channel_data)
st.plotly_chart(ratio_fig, use_container_width=True)

# Info section
with st.expander("ℹ️ About the Channel Model"):
    st.markdown(
        """
        ### Peak/Trough Channel Model

        This dashboard uses a **power-law fair value model** to identify Bitcoin market cycles:

        1. **Fair Value**: Calculated using a power law formula with exponent 5.93
           - `Fair Price = C × (days from genesis)^5.93`

        2. **Peak Detection**: Uses scipy peak detection algorithm to identify cycle tops
           - Prominence: 0.28
           - Distance: 600 days minimum between peaks

        3. **Trough Detection**: Identifies cycle bottoms using inverted peak detection

        4. **Channel Lines**: Linear regression fitted to peaks and troughs
           - Projects forward to 2030 for forward-looking guidance

        5. **Ratio Indicator**: Normalized position within the channel
           - 0% = At trough line (historically undervalued)
           - 100% = At peak line (historically overvalued)
           - Helps identify potential accumulation and distribution zones

        ### Data Source
        - Historical price data from **CoinCodex API**
        - Live prices from **Binance WebSocket** (BTCUSDT) with **Coinbase** fallback
        - Updated daily
        """
    )

# Auto-refresh live price (optional)
if st.checkbox("Enable auto-refresh (5 seconds)", value=False):
    time.sleep(5)
    st.rerun()
