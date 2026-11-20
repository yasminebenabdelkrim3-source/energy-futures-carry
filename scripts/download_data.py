"""Download (or refresh) the EIA futures panels and run calendar sanity checks.

Usage:
    python scripts/download_data.py               # all commodities, use cache if present
    python scripts/download_data.py --refresh wti  # force re-download of WTI
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from efc.config import COMMODITIES
from efc.data.calendar import expiry_dates
from efc.data.eia import load_prices
from efc.data.roll_detection import refine_expiries, roll_diagnostics


def _load_dotenv(path: Path = Path(".env")) -> None:
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keys", nargs="*", default=list(COMMODITIES), help="commodity keys")
    parser.add_argument("--refresh", action="store_true", help="ignore the local cache")
    args = parser.parse_args()
    _load_dotenv()

    print(
        f"{'commodity':<40} {'start':>10} {'end':>10} {'days':>6} {'expiries':>8}  "
        "calendar check: confirmed / inconclusive / misaligned (after refinement)"
    )
    for key in args.keys:
        com = COMMODITIES[key]
        df = load_prices(key, refresh=args.refresh)
        exp = expiry_dates(df.index, com.expiry_rule)
        before = roll_diagnostics(df, exp)["status"].value_counts()
        after = roll_diagnostics(df, refine_expiries(df, exp))["status"].value_counts()
        print(
            f"{com.name:<40} {df.index[0]:%Y-%m-%d} {df.index[-1]:%Y-%m-%d} {len(df):>6} "
            f"{len(exp):>8}  {before.get('confirmed', 0)} / {before.get('inconclusive', 0)} / "
            f"{before.get('misaligned', 0)} ({after.get('misaligned', 0)})"
        )

if __name__ == "__main__":
    main()
