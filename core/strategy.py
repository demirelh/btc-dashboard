"""Strategy logic for BTC rebalancing."""
from typing import List, Optional
import numpy as np

from core.models import StrategyParams, StrategyStep
from core.utils import clamp


class StrategyEngine:
    """Calculate rebalancing strategy based on channel ratio."""

    @staticmethod
    def sell_weight(ratio: float, sell_start: float, ladder: str) -> float:
        """
        Calculate target weight based on sell ladder function.

        Args:
            ratio: Current channel ratio (0-100%)
            sell_start: Ratio threshold to start selling
            ladder: Ladder type (g0, g1, g2)

        Returns:
            Target BTC weight (0-1)
        """
        if not np.isfinite(ratio):
            return 1.0
        if ratio <= sell_start:
            return 1.0
        if ratio >= 100:
            return 0.0

        width = 100 - sell_start
        if width <= 0:
            return 0.0

        # Normalize to 0-1 within sell range
        x = clamp((ratio - sell_start) / width, 0, 1)

        if ladder == "g0":
            # Soft/concave: 1 - x²
            return clamp(1 - x * x, 0, 1)
        elif ladder == "g2":
            # Aggressive/convex: (1 - x)²
            base = clamp(1 - x, 0, 1)
            return base * base
        else:
            # g1 default: linear 1 - x
            return clamp(1 - x, 0, 1)

    @staticmethod
    def target_weight(
        prev_weight: float,
        ratio: float,
        params: StrategyParams,
    ) -> float:
        """
        Calculate target weight with sell-only hysteresis and re-entry logic.

        Args:
            prev_weight: Previous weight
            ratio: Current channel ratio (0-100%)
            params: Strategy parameters

        Returns:
            Target BTC weight (0-1)
        """
        if not np.isfinite(ratio):
            return prev_weight

        # SELL REGIME: Only sell, never buy (hysteresis)
        if ratio >= params.sell_start:
            ladder_weight = StrategyEngine.sell_weight(
                ratio, params.sell_start, params.ladder
            )
            # Never increase exposure in sell regime
            return min(prev_weight, ladder_weight)

        # BELOW SELL START: Re-entry logic
        if params.reentry_mode == "instant":
            return 1.0
        elif params.reentry_mode == "wait":
            # Only return to 100% when ratio drops below buy threshold
            return 1.0 if ratio <= params.buy_threshold else prev_weight
        else:  # gradual
            # Smooth increase as ratio falls below sellStart
            denom = max(params.sell_start, 1e-9)
            f = clamp((params.sell_start - ratio) / denom, 0, 1)
            eased = f * f  # Smooth easing
            return clamp(prev_weight + (1 - prev_weight) * eased, 0, 1)

    @staticmethod
    def step_weight(
        prev_weight: float,
        ratio: float,
        params: StrategyParams,
    ) -> StrategyStep:
        """
        Calculate weight change and action for a single step.

        Args:
            prev_weight: Previous weight
            ratio: Current channel ratio (0-100%)
            params: Strategy parameters

        Returns:
            StrategyStep with weight, action, and tag
        """
        target = StrategyEngine.target_weight(prev_weight, ratio, params)
        delta = target - prev_weight

        if abs(delta) <= 1e-12:
            return StrategyStep(weight=prev_weight, action="HOLD", tag="hold")
        elif delta > 0:
            return StrategyStep(
                weight=target, action="BUY / REBALANCE UP", tag="buy"
            )
        else:
            return StrategyStep(
                weight=target, action="SELL / REBALANCE DOWN", tag="sell"
            )

    @staticmethod
    def compute_weight_series(
        ratios: List[float],
        dates: List[str],
        params: StrategyParams,
        start_idx: int = 0,
    ) -> tuple[List[Optional[float]], Optional[dict]]:
        """
        Compute weight series over time.

        Args:
            ratios: List of channel ratios
            dates: List of dates
            params: Strategy parameters
            start_idx: Index to start from

        Returns:
            Tuple of (weight_array, last_trade_info)
        """
        weights = [None] * len(ratios)
        weight = params.start_weight
        last_trade = None

        for i in range(start_idx, len(ratios)):
            ratio = float(ratios[i])
            step = StrategyEngine.step_weight(weight, ratio, params)

            changed = abs(step.weight - weight) > 1e-12
            if changed:
                last_trade = {
                    "date": dates[i],
                    "action": step.action,
                    "ratio": ratio,
                    "weight": step.weight,
                    "tag": step.tag,
                }

            weight = step.weight
            weights[i] = weight

        return weights, last_trade

    @staticmethod
    def get_ladder_hints(sell_start: float, ladder: str) -> dict:
        """
        Get weight values at specific ratio points.

        Args:
            sell_start: Sell start threshold
            ladder: Ladder type

        Returns:
            Dictionary with weights at 50%, 70%, 90% ratio
        """
        w50 = StrategyEngine.sell_weight(50, sell_start, ladder)
        w70 = StrategyEngine.sell_weight(70, sell_start, ladder)
        w90 = StrategyEngine.sell_weight(90, sell_start, ladder)

        return {
            "w50": w50 * 100,
            "w70": w70 * 100,
            "w90": w90 * 100,
        }
