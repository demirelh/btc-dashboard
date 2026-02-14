"""Utility functions for BTC Dashboard."""
import numpy as np
from typing import List, Tuple


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def max_drawdown(values: List[float]) -> float:
    """
    Calculate maximum drawdown from a series of equity values.

    Args:
        values: List of equity values

    Returns:
        Maximum drawdown as a negative decimal (e.g., -0.25 for 25% drawdown)
    """
    peak = float('-inf')
    max_dd = 0.0

    for v in values:
        if v is None or not np.isfinite(v):
            continue
        if v > peak:
            peak = v
        dd = (v / peak - 1) if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd

    return max_dd


def mean_std(values: List[float]) -> Tuple[int, float, float]:
    """
    Calculate mean and standard deviation using Welford's online algorithm.

    Args:
        values: List of numeric values

    Returns:
        Tuple of (count, mean, standard_deviation)
    """
    n = 0
    mean = 0.0
    M2 = 0.0

    for v0 in values:
        v = float(v0)
        if not np.isfinite(v):
            continue
        n += 1
        delta = v - mean
        mean += delta / n
        M2 += delta * (v - mean)

    variance = (M2 / (n - 1)) if n > 1 else 0
    std = np.sqrt(max(variance, 0))

    return n, mean, std


def price_for_ratio_pct(
    ratio_pct: float,
    trough_price: float,
    peak_price: float
) -> float:
    """
    Calculate price corresponding to a given ratio percentage.

    Args:
        ratio_pct: Ratio percentage (0-100)
        trough_price: Trough line price
        peak_price: Peak line price

    Returns:
        Price at the given ratio, or None if invalid
    """
    width = peak_price - trough_price
    if not np.isfinite(width) or width <= 0:
        return None
    return trough_price + (ratio_pct / 100.0) * width


def format_number(n: float, decimals: int = 2) -> str:
    """Format a number with thousand separators."""
    try:
        return f"{n:,.{decimals}f}"
    except:
        return str(n)


def format_usd(n: float) -> str:
    """Format a number as USD."""
    return f"${format_number(n, 0)}"


def format_pct(n: float, decimals: int = 2) -> str:
    """Format a number as percentage."""
    sign = "+" if n >= 0 else ""
    return f"{sign}{n * 100:.{decimals}f}%"
