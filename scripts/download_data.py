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
from efc.data.continuous import roll_jump_diagnostics
from efc.data.eia import load_prices


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

    for key in args.keys:
        com = COMMODITIES[key]
        df = load_prices(key, refresh=args.refresh)
        exp = expiry_dates(df.index, com.expiry_rule)
        diag = roll_jump_diagnostics(df, exp)
        n_bad = int(diag["mismatch"].sum()) if not diag.empty else 0
        print(
            f"{com.name:<42} {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}  "
            f"{len(df):>6} days  {len(exp):>4} expiries  "
            f"calendar mismatches: {n_bad}/{len(diag)}"
        )


if __name__ == "__main__":
    main()
