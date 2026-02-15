"""Reusable UI components for BTC Dashboard."""
import streamlit as st
from typing import Optional
import plotly.graph_objects as go

from core.models import ChannelData, BacktestResult, LivePrice
from core.utils import format_number, format_usd, format_pct
from ui.theme import get_plotly_theme, get_chart_colors


def _base_theme():
    """Return plotly theme without xaxis/yaxis to avoid duplicate keyword args."""
    theme = get_plotly_theme()
    return {k: v for k, v in theme.items() if k not in ("xaxis", "yaxis")}


def render_kpi_cards(
    channel_data: ChannelData,
    live_price: Optional[LivePrice] = None,
):
    """
    Render KPI cards at the top of the dashboard.

    Args:
        channel_data: Channel data with prices and ratios
        live_price: Optional live price information
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Preis (Close)",
            format_usd(channel_data.last_close),
            delta=f"Live: {format_usd(live_price.price) if live_price else '—'}"
            + (f" ({live_price.source})" if live_price else ""),
        )

    with col2:
        st.metric(
            "Kanal-Position",
            f"{channel_data.last_ratio:.1f}%",
            delta="Ratio (0% = Trough, 100% = Peak)",
        )

    with col3:
        st.metric(
            "Datenstand",
            channel_data.last_date,
            delta=f"Updated: {channel_data.meta.updated_utc[:10]}",
        )

    with col4:
        if live_price:
            status = "🟢 Connected" if live_price.source == "Binance" else "🟡 Fallback"
            st.metric(
                "Live Status",
                status,
                delta=f"{live_price.currency} via {live_price.source}",
            )
        else:
            st.metric("Live Status", "🔴 Offline", delta="No live data")


def plot_channel_chart(channel_data: ChannelData) -> go.Figure:
    """
    Create main channel chart with price, fair value, and ratio.

    Args:
        channel_data: Channel data to plot

    Returns:
        Plotly figure
    """
    theme = get_plotly_theme()
    colors = get_chart_colors()

    # Create figure with secondary y-axis
    fig = go.Figure()

    dates = channel_data.series.date
    ext_dates = channel_data.extended.date

    # Price and fair value
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=channel_data.series.price,
            name="Price",
            line=dict(color=colors["price"], width=1.5),
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=channel_data.series.fair,
            name="Fair Value",
            line=dict(color=colors["fair"], width=1.5, dash="dot"),
            mode="lines",
        )
    )

    # Peak and trough lines (extended)
    fig.add_trace(
        go.Scatter(
            x=ext_dates,
            y=channel_data.extended.peak_line_price,
            name="Peak Line",
            line=dict(color=colors["peak"], width=1.2, dash="dash"),
            mode="lines",
            opacity=0.7,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=ext_dates,
            y=channel_data.extended.trough_line_price,
            name="Trough Line",
            line=dict(color=colors["trough"], width=1.2, dash="dash"),
            mode="lines",
            opacity=0.7,
        )
    )

    # Update layout
    fig.update_layout(
        **_base_theme(),
        yaxis=dict(
            title="Price (USD)",
            type="log",
            **theme["yaxis"],
        ),
        xaxis=dict(title="Date", **theme["xaxis"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color="rgba(255,255,255,.78)"),
        ),
        height=600,
    )

    return fig


def plot_ratio_chart(channel_data: ChannelData) -> go.Figure:
    """
    Create ratio indicator chart (0-100%).

    Args:
        channel_data: Channel data to plot

    Returns:
        Plotly figure
    """
    theme = get_plotly_theme()
    colors = get_chart_colors()

    fig = go.Figure()

    dates = channel_data.series.date
    ratios = channel_data.series.ratio

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ratios,
            name="Kanal-Position",
            line=dict(color=colors["ratio"], width=2.2),
            mode="lines",
            fill="tozeroy",
            fillcolor=f"rgba(148,103,189,0.2)",
        )
    )

    # Add reference lines
    fig.add_hline(
        y=50, line_dash="dot", line_color="rgba(255,255,255,.3)", annotation_text="50%"
    )

    fig.update_layout(
        **_base_theme(),
        yaxis=dict(title="Ratio (%)", range=[0, 100], dtick=10, **theme["yaxis"]),
        xaxis=dict(title="Date", **theme["xaxis"]),
        height=300,
    )

    return fig


def plot_exposure_curve(
    ratios: list,
    weights: list,
    sell_start: float,
    current_ratio: float,
    current_weight: float,
) -> go.Figure:
    """
    Create exposure vs ratio curve chart.

    Args:
        ratios: List of ratio values (0-100)
        weights: List of target weights (0-100)
        sell_start: Sell start threshold
        current_ratio: Current ratio
        current_weight: Current weight

    Returns:
        Plotly figure
    """
    theme = get_plotly_theme()
    colors = get_chart_colors()

    fig = go.Figure()

    # Theoretical curve
    fig.add_trace(
        go.Scatter(
            x=ratios,
            y=weights,
            name="Target Exposure",
            line=dict(color=colors["ratio"], width=2.2),
            mode="lines",
        )
    )

    # Current position
    fig.add_trace(
        go.Scatter(
            x=[current_ratio],
            y=[current_weight],
            name="Current",
            mode="markers",
            marker=dict(size=10, color=colors["strat"]),
        )
    )

    # Sell start line
    fig.add_vline(
        x=sell_start,
        line_dash="dash",
        line_color="rgba(255,255,255,.22)",
        annotation_text=f"Sell Start {sell_start:.0f}%",
    )

    fig.update_layout(
        **_base_theme(),
        yaxis=dict(title="BTC Exposure (%)", range=[0, 100], **theme["yaxis"]),
        xaxis=dict(title="Kanal-Position / Ratio (%)", range=[0, 100], **theme["xaxis"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color="rgba(255,255,255,.78)"),
        ),
        height=400,
    )

    return fig


def plot_backtest_results(backtest: BacktestResult) -> go.Figure:
    """
    Create backtest results chart with dual y-axis.

    Args:
        backtest: Backtest results

    Returns:
        Plotly figure
    """
    theme = get_plotly_theme()
    colors = get_chart_colors()

    fig = go.Figure()

    # Weights on left axis
    weights_pct = [w * 100 if w is not None else None for w in backtest.weights]
    fig.add_trace(
        go.Scatter(
            x=backtest.dates,
            y=weights_pct,
            name="BTC Weight (%)",
            line=dict(color=colors["weight"], width=2),
            yaxis="y",
        )
    )

    # Equity curves on right axis
    fig.add_trace(
        go.Scatter(
            x=backtest.dates,
            y=backtest.hodl_equity,
            name="HODL (rel.)",
            line=dict(color=colors["hold"], width=1.4),
            yaxis="y2",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=backtest.dates,
            y=backtest.strategy_equity,
            name="Strategy (rel.)",
            line=dict(color=colors["strat"], width=2),
            yaxis="y2",
        )
    )

    fig.update_layout(
        **_base_theme(),
        yaxis=dict(title="BTC Weight (%)", range=[0, 100], **theme["yaxis"]),
        yaxis2=dict(
            title="Equity (relative)",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont={"color": "rgba(255,255,255,.70)"},
        ),
        xaxis=dict(title="Date", **theme["xaxis"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color="rgba(255,255,255,.78)"),
        ),
        height=500,
    )

    return fig


def plot_ratio_distribution(
    ratios: list,
    current_ratio: float,
    start_date: str = "",
) -> go.Figure:
    """
    Create ratio distribution histogram.

    Args:
        ratios: List of ratio values
        current_ratio: Current ratio value
        start_date: Start date for data

    Returns:
        Plotly figure
    """
    from core.utils import mean_std

    theme = get_plotly_theme()
    colors = get_chart_colors()

    n, mean, std = mean_std(ratios)
    m1 = max(0, min(100, mean - std))
    p1 = max(0, min(100, mean + std))

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=ratios,
            xbins=dict(start=0, end=101, size=1),
            marker_color=colors["ratio"],
            opacity=0.85,
            name="Frequency",
            hovertemplate="Position: %{x:.0f}%<br>Count: %{y}<extra></extra>",
        )
    )

    # Add mean and std dev lines
    fig.add_vline(
        x=mean,
        line_color="rgba(255,255,255,.45)",
        line_width=2,
        annotation_text=f"μ {mean:.1f}%",
        annotation_position="top",
    )

    fig.add_vline(
        x=m1,
        line_color="rgba(255,255,255,.28)",
        line_width=1,
        line_dash="dot",
        annotation_text=f"-1σ {m1:.1f}%",
        annotation_position="top",
    )

    fig.add_vline(
        x=p1,
        line_color="rgba(255,255,255,.28)",
        line_width=1,
        line_dash="dot",
        annotation_text=f"+1σ {p1:.1f}%",
        annotation_position="top",
    )

    # Current position
    fig.add_vline(
        x=current_ratio,
        line_color=colors["strat"],
        line_width=2,
        line_dash="dash",
        annotation_text=f"Now {current_ratio:.1f}%",
        annotation_position="top",
    )

    title_text = f"Since {start_date} | n={n} | μ={mean:.1f} | σ={std:.1f}" if start_date else f"n={n} | μ={mean:.1f} | σ={std:.1f}"

    fig.update_layout(
        **_base_theme(),
        yaxis=dict(title="Frequency", **theme["yaxis"]),
        xaxis=dict(
            title="Kanal-Position (%)",
            range=[0, 100],
            dtick=10,
            **theme["xaxis"],
        ),
        bargap=0.05,
        height=350,
        annotations=[
            dict(
                text=title_text,
                xref="paper",
                yref="paper",
                x=0.5,
                y=1.08,
                showarrow=False,
                font=dict(size=11, color="rgba(255,255,255,.70)"),
            )
        ],
    )

    return fig
