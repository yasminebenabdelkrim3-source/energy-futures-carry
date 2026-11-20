"""Download and cache NYMEX futures settlement prices from the EIA open-data API.

Each commodity is stored as one CSV in ``data/raw/<key>.csv`` with a ``date``
index and columns ``c1..cN`` (contract rank 1 = nearest expiry).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests

from efc.config import COMMODITIES, RAW_DATA_DIR, Commodity

EIA_BASE_URL = "https://api.eia.gov/v2/seriesid/{series_id}"
PAGE_SIZE = 5000  # EIA APIv2 returns at most 5000 rows per request


class EIAError(RuntimeError):
    pass


def _api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get("EIA_API_KEY")
    if not key:
        raise EIAError(
            "No EIA API key. Get a free one at https://www.eia.gov/opendata/register.php "
            "and set EIA_API_KEY (see .env.example)."
        )
    return key


def fetch_series(
    series_id: str,
    api_key: str | None = None,
    start: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> pd.Series:
    """Fetch one daily EIA series as a float Series indexed by date."""
    http = session or requests.Session()
    key = _api_key(api_key)
    rows: list[dict] = []
    offset = 0
    while True:
        params = {"api_key": key, "offset": offset, "length": PAGE_SIZE}
        if start:
            params["start"] = start
        resp = http.get(EIA_BASE_URL.format(series_id=series_id), params=params, timeout=timeout)
        if resp.status_code != 200:
            raise EIAError(f"{series_id}: HTTP {resp.status_code} - {resp.text[:200]}")
        payload = resp.json().get("response", {})
        page = payload.get("data", [])
        rows.extend(page)
        total = int(payload.get("total", len(rows)))
        offset += len(page)
        if not page or offset >= total:
            break

    if not rows:
        raise EIAError(f"{series_id}: empty response (check the series id)")

    df = pd.DataFrame(rows)
    out = pd.Series(
        pd.to_numeric(df["value"], errors="coerce").to_numpy(dtype=float),
        index=pd.to_datetime(df["period"]),
        name=series_id,
    )
    return out[~out.index.duplicated(keep="last")].sort_index()


def download_commodity(
    commodity: Commodity, api_key: str | None = None, start: str | None = None
) -> pd.DataFrame:
    """Download contracts 1..N of one commodity into a wide DataFrame (c1..cN)."""
    with requests.Session() as session:
        cols = {
            f"c{rank}": fetch_series(sid, api_key=api_key, start=start, session=session)
            for rank, sid in enumerate(commodity.eia_series, start=1)
        }
    df = pd.DataFrame(cols)
    df.index.name = "date"
    # keep only days where the front two contracts both settled
    return df.dropna(subset=["c1", "c2"])


def cache_path(key: str, data_dir: Path = RAW_DATA_DIR) -> Path:
    return data_dir / f"{key}.csv"


def load_prices(
    key: str,
    refresh: bool = False,
    api_key: str | None = None,
    data_dir: Path = RAW_DATA_DIR,
) -> pd.DataFrame:
    """Return the c1..cN price panel for ``key``, downloading it if not cached."""
    if key not in COMMODITIES:
        raise KeyError(f"Unknown commodity {key!r}; choose from {sorted(COMMODITIES)}")
    path = cache_path(key, data_dir)
    if path.exists() and not refresh:
        return pd.read_csv(path, index_col="date", parse_dates=["date"])
    df = download_commodity(COMMODITIES[key], api_key=api_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
    return df
