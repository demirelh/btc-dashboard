"""BTC Dashboard - Streamlit Main Entry Point."""
import streamlit as st

from ui.theme import apply_custom_theme

# Page configuration
st.set_page_config(
    page_title="BTC Dashboard",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom theme
apply_custom_theme()

# Main page content
st.title("₿ BTC Peak/Trough Channel Dashboard")
st.markdown(
    """
    **Modern Streamlit dashboard** for Bitcoin rebalancing strategy based on Peak/Trough channel analysis.

    - **Dashboard**: Live price, KPIs, and main channel chart
    - **Strategy**: Configure and backtest rebalancing strategies
    - **Backtest**: Compare strategy performance vs HODL
    - **Explanation**: Understand the channel derivation
    """
)

st.info(
    "👈 **Use the sidebar** to navigate between pages and configure strategy parameters."
)

# Show quick stats on home page
from core.data_store import load_channel_data
from core.price_feed import get_price_feed

try:
    # Load channel data
    channel_data = load_channel_data()

    if channel_data:
        st.markdown("### Quick Overview")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Last Close Price",
                f"${channel_data.last_close:,.0f}",
            )

        with col2:
            st.metric(
                "Channel Position",
                f"{channel_data.last_ratio:.1f}%",
            )

        with col3:
            st.metric(
                "Data Through",
                channel_data.last_date,
            )

        st.markdown(
            f"""
            **Channel Range**: ${channel_data.last_trough:,.0f} (Trough) → ${channel_data.last_peak:,.0f} (Peak)

            *Last updated: {channel_data.meta.updated_utc[:19]} UTC*
            """
        )
    else:
        st.warning(
            """
            **No channel data found.**

            Please run the data update first:
            ```python
            from core.data_store import update_channel_data
            update_channel_data()
            ```
            """
        )

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info(
        "Make sure you have run `python update.py` or use the update function to generate btc.json"
    )
