import json
from datetime import date, timedelta
import numpy as np
import pandas as pd
import requests
from numpy import log10
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression


def load_btc_daily_from_coincodex(start="2013-01-01", end=None, chunk_days=120):
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

        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()

        rows = data["BTC"]
        df = pd.DataFrame(rows).rename(columns={0: "timestamp", 1: "price_usd", 2: "volume_usd"})

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


def compute_all(df_full):
    # --- dein Setup ---
    df_full = df_full.copy()
    df_full["Date"] = pd.to_datetime(df_full["Start"])
    df_full = df_full.sort_values("Date").dropna().reset_index(drop=True)
    df_full["Price"] = df_full["Close"]

    genesis = pd.Timestamp("2009-01-03")
    df_full["days"] = (df_full["Date"] - genesis).dt.days + 1

    B_EXP = 5.93
    log_days = log10(df_full["days"].values)
    log_price = log10(df_full["Price"].values)

    log_C = np.mean(log_price - B_EXP * log_days)
    C_SCALE = 10 ** log_C

    df_full["Fair"] = C_SCALE * (df_full["days"] ** B_EXP)
    df_full["R"] = df_full["Price"] / df_full["Fair"]

    df_full = df_full[df_full["R"] > 0].copy()
    df_full["log10_R"] = np.log10(df_full["R"])

    # Peaks/Troughs
    data_to_analyze = df_full["log10_R"].values
    peak_prominence = 0.28
    peak_distance = 600
    peak_width = 5

    trough_prominence = 0.28
    trough_distance = 600
    trough_width = 5

    peaks_indices, _ = find_peaks(
        data_to_analyze, prominence=peak_prominence, distance=peak_distance, width=peak_width
    )
    troughs_indices, _ = find_peaks(
        -data_to_analyze, prominence=trough_prominence, distance=trough_distance, width=trough_width
    )

    peak_days = df_full["days"].iloc[peaks_indices].values.reshape(-1, 1)
    peak_vals = df_full["log10_R"].iloc[peaks_indices].values

    trough_days = df_full["days"].iloc[troughs_indices].values.reshape(-1, 1)
    trough_vals = df_full["log10_R"].iloc[troughs_indices].values

    peak_reg = LinearRegression().fit(peak_days, peak_vals)
    trough_reg = LinearRegression().fit(trough_days, trough_vals)

    # Extend to 2030
    last_date = df_full["Date"].max()
    target_date = pd.Timestamp("2030-12-31")

    all_days_original = df_full["days"].values
    num_additional_days = (target_date - last_date).days + 1
    additional_days = np.arange(all_days_original[-1] + 1, all_days_original[-1] + 1 + num_additional_days)
    all_days_extended = np.concatenate((all_days_original, additional_days))
    all_days_ext_2d = all_days_extended.reshape(-1, 1)

    all_dates_extended = pd.to_datetime(
        list(df_full["Date"].values) +
        list((genesis + pd.to_timedelta(additional_days - 1, unit="D")).to_pydatetime())
    )

    peak_log10 = peak_reg.predict(all_days_ext_2d)
    trough_log10 = trough_reg.predict(all_days_ext_2d)

    peak_R = 10 ** peak_log10
    trough_R = 10 ** trough_log10

    extended_fair = C_SCALE * (all_days_extended ** B_EXP)
    peak_price_line = peak_R * extended_fair
    trough_price_line = trough_R * extended_fair

    # Ratio indicator (nur im Originalbereich)
    current_peak = peak_price_line[:len(df_full)]
    current_trough = trough_price_line[:len(df_full)]
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
        }
    }

    return payload


def main():
    df = load_btc_daily_from_coincodex(start="2013-01-01")
    payload = compute_all(df)

    out_path = "/home/pi/btc-dashboard/web/data/btc.json"
    with open(out_path, "w") as f:
        json.dump(payload, f)

    print("Wrote:", out_path, "end:", payload["meta"]["end"])


if __name__ == "__main__":
    main()
