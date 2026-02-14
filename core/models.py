"""Data models for BTC Dashboard."""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class ChannelMeta(BaseModel):
    """Metadata for channel data."""
    start: str
    end: str
    updated_utc: str


class ChannelSeries(BaseModel):
    """Historical price and channel data."""
    date: List[str]
    price: List[float]
    fair: List[float]
    log10_r: List[float]
    ratio: List[float]


class ExtendedChannelData(BaseModel):
    """Extended channel projections."""
    date: List[str]
    fair: List[float]
    peak_line_price: List[float]
    trough_line_price: List[float]
    peak_line_log10: List[float]
    trough_line_log10: List[float]


class ChannelData(BaseModel):
    """Complete channel data structure."""
    meta: ChannelMeta
    series: ChannelSeries
    extended: ExtendedChannelData

    @property
    def last_close(self) -> float:
        """Get the last closing price."""
        return self.series.price[-1] if self.series.price else 0.0

    @property
    def last_ratio(self) -> float:
        """Get the last ratio value."""
        return self.series.ratio[-1] if self.series.ratio else 0.0

    @property
    def last_date(self) -> str:
        """Get the last date."""
        return self.series.date[-1] if self.series.date else ""

    @property
    def last_trough(self) -> float:
        """Get the last trough price."""
        idx = len(self.series.price) - 1
        if idx < len(self.extended.trough_line_price):
            return self.extended.trough_line_price[idx]
        return 0.0

    @property
    def last_peak(self) -> float:
        """Get the last peak price."""
        idx = len(self.series.price) - 1
        if idx < len(self.extended.peak_line_price):
            return self.extended.peak_line_price[idx]
        return 0.0


@dataclass
class StrategyParams:
    """Strategy configuration parameters."""
    ladder: str = "g1"  # g0, g1, g2
    sell_start: float = 46.0
    buy_threshold: float = 14.0
    reentry_mode: str = "instant"  # instant, wait, gradual
    start_weight: float = 1.0
    start_date: str = "2018-01-01"


@dataclass
class StrategyStep:
    """Single strategy step result."""
    weight: float
    action: str
    tag: str  # buy, sell, hold


@dataclass
class BacktestResult:
    """Backtest results vs HODL."""
    dates: List[str]
    weights: List[float]
    strategy_equity: List[float]
    hodl_equity: List[float]
    strategy_return: float
    hodl_return: float
    strategy_max_drawdown: float
    hodl_max_drawdown: float
    last_trade: Optional[dict] = None

    @property
    def performance_delta(self) -> float:
        """Calculate performance difference vs HODL."""
        return self.strategy_return - self.hodl_return


@dataclass
class LivePrice:
    """Live price information."""
    price: float
    currency: str
    source: str  # Binance, Coinbase
    timestamp: float
