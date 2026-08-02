#!/usr/bin/env python3
"""
cftc_fetch.py
Pulls weekly CFTC Traders in Financial Futures (TFF, Futures Only) data for
the S&P 500 E-mini contract, isolates the "Leveraged Funds" net position
(hedge funds / CTAs / CPOs), and caches it to CSV. No API key required.

Source: CFTC Socrata Public Reporting Environment, dataset gpe5-46if
(TFF Futures Only). Data released Fridays ~3:30pm ET, covering the prior
Tuesday's positions.
"""

import sys
import datetime as dt
from pathlib import Path
import requests
import pandas as pd

BASE_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
CACHE_DIR = Path("data/cftc")
OUT_FILE = CACHE_DIR / "sp500_leveraged_funds.csv"

# CFTC's contract naming has shifted over time (E-MINI vs consolidated
# E-MINI+MICRO reporting) -- match broadly and let the caller inspect
# contract_market_name if multiple rows come back for the same date.
PARAMS = {
    "$where": "market_and_exchange_names like '%S&P 500%'",
    "$order": "report_date_as_yyyy_mm_dd DESC",
    "$limit": "5000",
}

def fetch() -> pd.DataFrame:
    resp = requests.get(BASE_URL, params=PARAMS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError("No rows returned from CFTC TFF endpoint.")

    df = pd.DataFrame(data)
    keep = [
        "report_date_as_yyyy_mm_dd",
        "market_and_exchange_names",
        "open_interest_all",
        "lev_money_positions_long",
        "lev_money_positions_short",
        "lev_money_positions_spread",
    ]
    df = df[[c for c in keep if c in df.columns]].copy()
    df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    for c in ["open_interest_all", "lev_money_positions_long",
              "lev_money_positions_short", "lev_money_positions_spread"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["lev_net_position"] = df["lev_money_positions_long"] - df["lev_money_positions_short"]
    df = df.sort_values("report_date_as_yyyy_mm_dd").reset_index(drop=True)
    return df

def update_cache(df_new: pd.DataFrame, path: Path) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        df_old = pd.read_csv(path, parse_dates=["report_date_as_yyyy_mm_dd"])
        merged = pd.concat([df_old, df_new]).drop_duplicates(
            subset=["report_date_as_yyyy_mm_dd", "market_and_exchange_names"],
            keep="last",
        ).sort_values("report_date_as_yyyy_mm_dd")
    else:
        merged = df_new
    merged.to_csv(path, index=False)
    return merged

def main():
    print(f"[{dt.datetime.now()}] Fetching CFTC TFF S&P 500 leveraged funds positions...")
    try:
        df_new = fetch()
        merged = update_cache(df_new, OUT_FILE)
        latest = merged.iloc[-1]
        print(f"  {latest['report_date_as_yyyy_mm_dd'].strftime('%Y-%m-%d')} "
              f"({latest['market_and_exchange_names']}): "
              f"net leveraged-fund position = {latest['lev_net_position']:.0f} contracts "
              f"[{len(merged)} rows]")
    except Exception as e:
        print(f"  FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    print("\nCFTC leveraged funds data updated successfully.")

if __name__ == "__main__":
    main()
