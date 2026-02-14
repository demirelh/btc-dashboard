"""Backtest engine for strategy vs HODL comparison."""
from typing import List, Optional
import numpy as np

from core.models import BacktestResult, StrategyParams
from core.strategy import StrategyEngine
from core.utils import max_drawdown


class BacktestEngine:
    """Backtest strategy performance vs HODL."""

    @staticmethod
    def run_backtest(
        dates: List[str],
        prices: List[float],
        ratios: List[float],
        params: StrategyParams,
        start_idx: int = 0,
    ) -> BacktestResult:
        """
        Run backtest simulation.

        Args:
            dates: List of dates
            prices: List of prices
            ratios: List of ratios
            params: Strategy parameters
            start_idx: Index to start backtest from

        Returns:
            BacktestResult with equity curves and metrics
        """
        # Compute weight series
        weights, last_trade = StrategyEngine.compute_weight_series(
            ratios, dates, params, start_idx
        )

        # Get data slice from start_idx
        dates_slice = dates[start_idx:]
        prices_slice = [float(p) for p in prices[start_idx:]]
        weights_slice = weights[start_idx:]

        # Initialize equity curves
        n = len(dates_slice)
        hodl_equity = [None] * n
        strategy_equity = [None] * n
        hodl_equity[0] = 1.0
        strategy_equity[0] = 1.0

        # Compute daily returns
        for i in range(n - 1):
            p0, p1 = prices_slice[i], prices_slice[i + 1]
            wi = weights_slice[i]

            if not np.isfinite(p0) or not np.isfinite(p1) or p0 <= 0 or wi is None:
                break

            # BTC return
            btc_return = p1 / p0

            # HODL equity (100% BTC)
            hodl_equity[i + 1] = (hodl_equity[i] or 1.0) * btc_return

            # Strategy equity (wi% BTC + (1-wi)% cash)
            portfolio_return = wi * btc_return + (1 - wi) * 1.0
            strategy_equity[i + 1] = (strategy_equity[i] or 1.0) * portfolio_return

        # Calculate final metrics
        last_hodl = hodl_equity[-1] if hodl_equity[-1] is not None else 1.0
        last_strat = strategy_equity[-1] if strategy_equity[-1] is not None else 1.0

        hodl_return = last_hodl - 1.0
        strat_return = last_strat - 1.0

        # Calculate drawdowns
        valid_hodl = [v for v in hodl_equity if v is not None]
        valid_strat = [v for v in strategy_equity if v is not None]

        hodl_dd = max_drawdown(valid_hodl)
        strat_dd = max_drawdown(valid_strat)

        return BacktestResult(
            dates=dates_slice,
            weights=weights_slice,
            strategy_equity=strategy_equity,
            hodl_equity=hodl_equity,
            strategy_return=strat_return,
            hodl_return=hodl_return,
            strategy_max_drawdown=strat_dd,
            hodl_max_drawdown=hodl_dd,
            last_trade=last_trade,
        )

    @staticmethod
    def get_next_triggers(
        current_ratio: float,
        sell_start: float,
        buy_threshold: float,
        reentry_mode: str,
        last_trough: float,
        last_peak: float,
    ) -> dict:
        """
        Calculate next trigger points.

        Args:
            current_ratio: Current ratio (0-100%)
            sell_start: Sell start threshold
            buy_threshold: Buy threshold for wait mode
            reentry_mode: Re-entry mode
            last_trough: Last trough price
            last_peak: Last peak price

        Returns:
            Dictionary with next sell and buy trigger information
        """
        from core.utils import price_for_ratio_pct

        result = {
            "next_sell_ratio": None,
            "next_sell_price": None,
            "next_buy_ratio": None,
            "next_buy_price": None,
            "sell_text": "",
            "buy_text": "",
        }

        if current_ratio < sell_start:
            # Below sell threshold
            result["next_sell_ratio"] = sell_start
            result["next_sell_price"] = price_for_ratio_pct(
                sell_start, last_trough, last_peak
            )
            result["sell_text"] = f"SELL begins @ Ratio {sell_start:.1f}%"

            if reentry_mode == "wait":
                result["next_buy_ratio"] = buy_threshold
                result["next_buy_price"] = price_for_ratio_pct(
                    buy_threshold, last_trough, last_peak
                )
                result["buy_text"] = f"RE-ENTRY: 100% @ Ratio {buy_threshold:.1f}%"
            elif reentry_mode == "gradual":
                result["buy_text"] = "UP: higher BTC % as ratio falls"
            else:
                result["buy_text"] = "BUY: below SellStart = 100%"

        else:
            # Above or at sell threshold (in sell regime)
            next_ratio = min(current_ratio + 1, 100)
            result["next_sell_ratio"] = next_ratio
            result["next_sell_price"] = price_for_ratio_pct(
                next_ratio, last_trough, last_peak
            )
            result["sell_text"] = f"DOWN: lower BTC % @ Ratio {next_ratio:.1f}%"

            if reentry_mode == "wait":
                result["next_buy_ratio"] = buy_threshold
                result["next_buy_price"] = price_for_ratio_pct(
                    buy_threshold, last_trough, last_peak
                )
                result["buy_text"] = (
                    f"RE-ENTRY: 100% only @ Ratio {buy_threshold:.1f}%"
                )
            elif reentry_mode == "gradual":
                result["buy_text"] = f"UP: below SellStart ({sell_start:.1f}%) gradually"
            else:
                result["buy_text"] = f"BUY: below SellStart ({sell_start:.1f}%) instantly 100%"

        return result
