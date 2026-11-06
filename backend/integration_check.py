"""
Manual integration script — calls the LIVE Elexon BMRS API.

Purpose: verify real API connectivity, response shape, and record counts for
January 2026.  NOT for automated CI — requires network access.

Usage (from the backend/ directory):
    python integration_check.py

Environment:
    No API key required. Elexon BMRS is a public API.
"""

import sys
import logging
import json
from datetime import timezone

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("integration_check")

# Ensure app is importable from backend/
sys.path.insert(0, ".")

from app.services.elexon import (
    fetch_actual_generation,
    fetch_wind_forecasts,
    select_day_ahead_forecasts,
    DAY_AHEAD_CUTOFF_HOUR_UTC,
)


def _summarise_actuals(records: list) -> None:
    if not records:
        print("  [!] No actual wind records returned.")
        return
    gens = [r["generation"] for r in records]
    dates = [r["start_time"].date() for r in records]
    print(f"  Records      : {len(records)}")
    print(f"  Date range   : {min(dates)} → {max(dates)}")
    print(f"  Generation   : min={min(gens):.1f} MW  max={max(gens):.1f} MW  "
          f"mean={sum(gens)/len(gens):.1f} MW")
    print(f"  Sample record: {json.dumps({k: str(v) for k,v in records[0].items()}, indent=4)}")


def _summarise_forecasts(records: list, label: str = "Forecast") -> None:
    if not records:
        print(f"  [!] No {label} records returned.")
        return
    gens = [r["generation"] for r in records]
    start_dates = [r["start_time"].date() for r in records]
    pub_dates = [r["publish_time"].date() for r in records]
    print(f"  Records          : {len(records)}")
    print(f"  Delivery range   : {min(start_dates)} → {max(start_dates)}")
    print(f"  Publish range    : {min(pub_dates)} → {max(pub_dates)}")
    print(f"  Generation       : min={min(gens):.1f} MW  max={max(gens):.1f} MW  "
          f"mean={sum(gens)/len(gens):.1f} MW")
    print(f"  Sample record    : {json.dumps({k: str(v) for k,v in records[0].items()}, indent=4)}")


def main() -> None:
    print("=" * 60)
    print("Wind Forecast Analytics — Live Elexon API Integration Check")
    print("=" * 60)

    # --- Actuals ---
    print("\n[1/3] Fetching FUELHH actual wind generation (January 2026)...")
    try:
        actuals = fetch_actual_generation()
        print(f"  OK — {len(actuals)} records returned.")
        _summarise_actuals(actuals)
    except Exception as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)

    # --- All forecasts ---
    print("\n[2/3] Fetching WINDFOR forecasts (published Dec 31 2025 – Jan 31 2026)...")
    try:
        forecasts = fetch_wind_forecasts()
        print(f"  OK — {len(forecasts)} records returned.")
        _summarise_forecasts(forecasts, label="All forecasts")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)

    # --- Day-ahead selection ---
    print(f"\n[3/3] Applying day-ahead cutoff (cutoff_hour_utc={DAY_AHEAD_CUTOFF_HOUR_UTC})...")
    try:
        da_forecasts = select_day_ahead_forecasts(
            forecasts, cutoff_hour_utc=DAY_AHEAD_CUTOFF_HOUR_UTC
        )
        print(f"  OK — {len(da_forecasts)} day-ahead records selected.")
        _summarise_forecasts(da_forecasts, label="Day-ahead filtered")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Integration check PASSED.")
    print("=" * 60)


if __name__ == "__main__":
    main()

