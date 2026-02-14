"""Channel calculation and data management."""
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
from numpy import log10
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression

from core.models import ChannelData


class ChannelCalculator:
    """Calculate BTC price channel using power law and peak/trough detection."""

    def __init__(
        self,
        b_exp: float = 5.93,
        genesis_date: str = "2009-01-03",
        peak_prominence: float = 0.28,
        peak_distance: int = 600,
        peak_width: int = 5,
    ):
        """
        Initialize channel calculator.

        Args:
            b_exp: Power law exponent
            genesis_date: Bitcoin genesis date
            peak_prominence: Peak detection prominence parameter
            peak_distance: Peak detection distance parameter
            peak_width: Peak detection width parameter
        """
        self.b_exp = b_exp
        self.genesis = pd.Timestamp(genesis_date)
        self.peak_prominence = peak_prominence
        self.peak_distance = peak_distance
        self.peak_width = peak_width

    def load_btc_daily_from_coincodex(
        self,
        start: str = "2013-01-01",
        end: Optional[str] = None,
        chunk_days: int = 120,
    ) -> pd.DataFrame:
        """
        Load daily BTC price data from CoinCodex API.

        Args:
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD), defaults to yesterday
            chunk_days: Number of days per API request

        Returns:
            DataFrame with columns ['Start', 'Close']
        """
        if end is None:
            end = (date.today() - timedelta(days=1)).isoformat()

        start_date = pd.to_datetime(start).date()
        end_date = pd.to_datetime(end).date()

        out = []
        cur = start_date

        while cur <= end_date:
            chunk_end = min(cur + timedelta(days=chunk_days - 1), end_date)
            days = (chunk_end - cur).days + 1

            samples = min(2000, max(250, days * 8))
            url = (
                "https://coincodex.com/api/coincodex/get_coin_history/"
                f"BTC/{cur:%Y-%m-%d}/{chunk_end:%Y-%m-%d}/{samples}"
            )

            r = requests.get(
                url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
            )
            r.raise_for_status()
            data = r.json()

            rows = data["BTC"]
            df = pd.DataFrame(rows).rename(
                columns={0: "timestamp", 1: "price_usd", 2: "volume_usd"}
            )

            ts = df["timestamp"].astype("int64")
            unit = "ms" if ts.max() > 1_000_000_000_000 else "s"
            dt_utc = pd.to_datetime(ts, unit=unit, utc=True)

            df["Date"] = dt_utc.dt.date
            df["dt"] = dt_utc

            daily = (
                df.sort_values("dt")
                .groupby("Date", as_index=False)
                .last()[["Date", "price_usd"]]
                .rename(columns={"price_usd": "Close"})
            )

            out.append(daily)
            cur = chunk_end + timedelta(days=1)

        hist = (
            pd.concat(out, ignore_index=True)
            .drop_duplicates(subset=["Date"], keep="last")
            .sort_values("Date")
            .reset_index(drop=True)
        )

        hist["Start"] = pd.to_datetime(hist["Date"])
        return hist[["Start", "Close"]]

    def compute_channel(self, df_full: pd.DataFrame) -> dict:
        """
        Compute channel data from historical prices.

        Args:
            df_full: DataFrame with columns ['Start', 'Close']

        Returns:
            Dictionary with channel data (JSON-ready)
        """
        df_full = df_full.copy()
        df_full["Date"] = pd.to_datetime(df_full["Start"])
        df_full = df_full.sort_values("Date").dropna().reset_index(drop=True)
        df_full["Price"] = df_full["Close"]

        df_full["days"] = (df_full["Date"] - self.genesis).dt.days + 1

        # Power law fair value calculation
        log_days = log10(df_full["days"].values)
        log_price = log10(df_full["Price"].values)

        log_C = np.mean(log_price - self.b_exp * log_days)
        C_SCALE = 10 ** log_C

        df_full["Fair"] = C_SCALE * (df_full["days"] ** self.b_exp)
        df_full["R"] = df_full["Price"] / df_full["Fair"]

        df_full = df_full[df_full["R"] > 0].copy()
        df_full["log10_R"] = np.log10(df_full["R"])

        # Peak/Trough detection
        data_to_analyze = df_full["log10_R"].values

        peaks_indices, _ = find_peaks(
            data_to_analyze,
            prominence=self.peak_prominence,
            distance=self.peak_distance,
            width=self.peak_width,
        )
        troughs_indices, _ = find_peaks(
            -data_to_analyze,
            prominence=self.peak_prominence,
            distance=self.peak_distance,
            width=self.peak_width,
        )

        peak_days = df_full["days"].iloc[peaks_indices].values.reshape(-1, 1)
        peak_vals = df_full["log10_R"].iloc[peaks_indices].values

        trough_days = df_full["days"].iloc[troughs_indices].values.reshape(-1, 1)
        trough_vals = df_full["log10_R"].iloc[troughs_indices].values

        # Linear regression for peak/trough lines
        peak_reg = LinearRegression().fit(peak_days, peak_vals)
        trough_reg = LinearRegression().fit(trough_days, trough_vals)

        # Extend to 2030
        last_date = df_full["Date"].max()
        target_date = pd.Timestamp("2030-12-31")

        all_days_original = df_full["days"].values
        num_additional_days = (target_date - last_date).days + 1
        additional_days = np.arange(
            all_days_original[-1] + 1,
            all_days_original[-1] + 1 + num_additional_days,
        )
        all_days_extended = np.concatenate((all_days_original, additional_days))
        all_days_ext_2d = all_days_extended.reshape(-1, 1)

        all_dates_extended = pd.to_datetime(
            list(df_full["Date"].values)
            + list((self.genesis + pd.to_timedelta(additional_days - 1, unit="D")).to_pydatetime())
        )

        peak_log10 = peak_reg.predict(all_days_ext_2d)
        trough_log10 = trough_reg.predict(all_days_ext_2d)

        peak_R = 10 ** peak_log10
        trough_R = 10 ** trough_log10

        extended_fair = C_SCALE * (all_days_extended ** self.b_exp)
        peak_price_line = peak_R * extended_fair
        trough_price_line = trough_R * extended_fair

        # Ratio indicator (0-100%)
        current_peak = peak_price_line[: len(df_full)]
        current_trough = trough_price_line[: len(df_full)]
        price = df_full["Price"].values
        width = current_peak - current_trough

        ratio = np.zeros_like(price, dtype=float)
        ok = width > 0
        ratio[ok] = (price[ok] - current_trough[ok]) / width[ok] * 100
        ratio = np.clip(ratio, 0, 100)

        # JSON-ready payload
        payload = {
            "meta": {
                "start": str(df_full["Date"].iloc[0].date()),
                "end": str(df_full["Date"].iloc[-1].date()),
                "updated_utc": pd.Timestamp.utcnow().isoformat(),
            },
            "series": {
                "date": [d.strftime("%Y-%m-%d") for d in df_full["Date"]],
                "price": df_full["Price"].astype(float).tolist(),
                "fair": df_full["Fair"].astype(float).tolist(),
                "log10_r": df_full["log10_R"].astype(float).tolist(),
                "ratio": ratio.astype(float).tolist(),
            },
            "extended": {
                "date": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in all_dates_extended],
                "fair": extended_fair.astype(float).tolist(),
                "peak_line_price": peak_price_line.astype(float).tolist(),
                "trough_line_price": trough_price_line.astype(float).tolist(),
                "peak_line_log10": peak_log10.astype(float).tolist(),
                "trough_line_log10": trough_log10.astype(float).tolist(),
            },
        }

        return payload


def load_channel_data(file_path: str = "web/data/btc.json") -> Optional[ChannelData]:
    """
    Load channel data from JSON file.

    Args:
        file_path: Path to btc.json file

    Returns:
        ChannelData object or None if file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        return None

    with open(path, "r") as f:
        data = json.load(f)

    return ChannelData(**data)


def save_channel_data(data: dict, file_path: str = "web/data/btc.json"):
    """
    Save channel data to JSON file.

    Args:
        data: Channel data dictionary
        file_path: Path to save JSON file
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f)


def update_channel_data(
    start: str = "2013-01-01",
    output_path: str = "web/data/btc.json",
) -> dict:
    """
    Fetch fresh data and recompute channel.

    Args:
        start: Start date for historical data
        output_path: Path to save updated data

    Returns:
        Updated channel data dictionary
    """
    calculator = ChannelCalculator()
    df = calculator.load_btc_daily_from_coincodex(start=start)
    payload = calculator.compute_channel(df)
    save_channel_data(payload, output_path)
    return payload
