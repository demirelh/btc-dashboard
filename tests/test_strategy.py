"""Unit tests for core strategy logic."""
import pytest
from core.models import StrategyParams
from core.strategy import StrategyEngine
from core.utils import clamp, max_drawdown, mean_std


def test_clamp():
    """Test clamp utility function."""
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10
    assert clamp(7.5, 0, 10) == 7.5


def test_max_drawdown():
    """Test max drawdown calculation."""
    # No drawdown
    equity = [1.0, 1.1, 1.2, 1.3]
    assert max_drawdown(equity) == 0.0

    # 50% drawdown
    equity = [1.0, 2.0, 1.0]
    assert abs(max_drawdown(equity) - (-0.5)) < 1e-9

    # Multiple drawdowns, track worst
    equity = [1.0, 1.5, 1.2, 1.8, 0.9]
    dd = max_drawdown(equity)
    assert dd == 0.9 / 1.8 - 1  # About -0.5


def test_mean_std():
    """Test mean and std calculation."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    n, mean, std = mean_std(values)
    assert n == 5
    assert abs(mean - 3.0) < 1e-9
    assert abs(std - 1.5811388300841898) < 1e-6


def test_sell_weight_g0():
    """Test g0 sell ladder (soft)."""
    # Below sell start
    assert StrategyEngine.sell_weight(30, 46, "g0") == 1.0

    # At sell start
    assert StrategyEngine.sell_weight(46, 46, "g0") == 1.0

    # At peak
    assert StrategyEngine.sell_weight(100, 46, "g0") == 0.0

    # Midpoint (ratio=73, x=0.5)
    # g0: 1 - 0.5² = 0.75
    w = StrategyEngine.sell_weight(73, 46, "g0")
    assert abs(w - 0.75) < 1e-9


def test_sell_weight_g1():
    """Test g1 sell ladder (linear)."""
    # Below sell start
    assert StrategyEngine.sell_weight(30, 46, "g1") == 1.0

    # At peak
    assert StrategyEngine.sell_weight(100, 46, "g1") == 0.0

    # Midpoint (ratio=73, x=0.5)
    # g1: 1 - 0.5 = 0.5
    w = StrategyEngine.sell_weight(73, 46, "g1")
    assert abs(w - 0.5) < 1e-9


def test_sell_weight_g2():
    """Test g2 sell ladder (aggressive)."""
    # Below sell start
    assert StrategyEngine.sell_weight(30, 46, "g2") == 1.0

    # At peak
    assert StrategyEngine.sell_weight(100, 46, "g2") == 0.0

    # Midpoint (ratio=73, x=0.5)
    # g2: (1 - 0.5)² = 0.25
    w = StrategyEngine.sell_weight(73, 46, "g2")
    assert abs(w - 0.25) < 1e-9


def test_target_weight_instant_reentry():
    """Test instant re-entry mode."""
    params = StrategyParams(
        ladder="g1",
        sell_start=46.0,
        buy_threshold=14.0,
        reentry_mode="instant",
        start_weight=1.0,
    )

    # Below sell start -> instant 100%
    w = StrategyEngine.target_weight(0.5, 30, params)
    assert w == 1.0

    # In sell regime -> follow ladder
    w = StrategyEngine.target_weight(1.0, 73, params)
    assert abs(w - 0.5) < 1e-9


def test_target_weight_wait_reentry():
    """Test wait re-entry mode."""
    params = StrategyParams(
        ladder="g1",
        sell_start=46.0,
        buy_threshold=14.0,
        reentry_mode="wait",
        start_weight=1.0,
    )

    # Above buy threshold but below sell start -> hold
    w = StrategyEngine.target_weight(0.5, 30, params)
    assert w == 0.5  # Hold current weight

    # Below buy threshold -> 100%
    w = StrategyEngine.target_weight(0.5, 10, params)
    assert w == 1.0

    # In sell regime -> follow ladder
    w = StrategyEngine.target_weight(1.0, 73, params)
    assert abs(w - 0.5) < 1e-9


def test_sell_only_hysteresis():
    """Test sell-only hysteresis in sell regime."""
    params = StrategyParams(
        ladder="g1",
        sell_start=46.0,
        buy_threshold=14.0,
        reentry_mode="instant",
        start_weight=1.0,
    )

    # In sell regime at 70% with prev weight 0.4
    # Ladder says 0.44, but we should stay at 0.4 (no buying)
    w = StrategyEngine.target_weight(0.4, 70, params)
    assert w == 0.4

    # In sell regime at 90% with prev weight 0.4
    # Ladder says 0.185, so we reduce
    w = StrategyEngine.target_weight(0.4, 90, params)
    assert w < 0.4


def test_ladder_hints():
    """Test ladder hint values."""
    hints = StrategyEngine.get_ladder_hints(46, "g1")

    # At 50%, x = (50-46)/(100-46) = 4/54 ≈ 0.074
    # g1: 1 - 0.074 = 0.926
    assert hints["w50"] > 90

    # At 90%, x = (90-46)/(100-46) = 44/54 ≈ 0.815
    # g1: 1 - 0.815 = 0.185
    assert 15 < hints["w90"] < 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
