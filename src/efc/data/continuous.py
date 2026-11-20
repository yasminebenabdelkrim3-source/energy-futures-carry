"""Turn rank-based contract prices (c1..cN) into a tradable return series.

EIA's "contract 1" is a *label*: the day after the front contract expires, the old
contract 2 becomes contract 1. Naively taking ``c1.pct_change()`` therefore mixes
two different contracts on roll days and creates fake jumps (the calendar spread).

We instead simulate a position that
- holds contract rank 1, and
- rolls into rank 2 ``roll_days`` trading days before the front expiry, so it never
  holds a contract into its last trading day (avoids the delivery squeeze, e.g.
  WTI on 20 April 2020 at -37 USD/bbl).

Day-t return is computed on the *same physical contract* held at t-1:
    r_t = P_t[contract] / P_{t-1}[contract] - 1
where the contract's rank drops by one on the first trading day after an expiry.

Futures returns are excess returns (no cash is invested); collateral interest is
ignored here and can be added at the portfolio level.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def held_rank(index: pd.DatetimeIndex, expiries: pd.DatetimeIndex, roll_days: int = 5) -> pd.Series:
    """Contract rank held at the close of each day (1 normally, 2 inside the roll window).

    The roll window is the last ``roll_days`` trading days up to and including expiry.
    """
    if roll_days < 1:
        raise ValueError("roll_days must be >= 1 so the position never sits on expiry day")
    idx = pd.DatetimeIndex(index)
    rank = np.ones(len(idx), dtype=int)
    pos = idx.get_indexer(expiries)
    for p in pos[pos >= 0]:
        rank[max(0, p - roll_days + 1) : p + 1] = 2
    return pd.Series(rank, index=idx, name="held_rank")


def rolled_returns(
    prices: pd.DataFrame, expiries: pd.DatetimeIndex, roll_days: int = 5
) -> pd.Series:
    """Daily returns of the rolled front-month position.

    Parameters
    ----------
    prices : DataFrame with columns c1..cN indexed by trading day.
    expiries : last trading day of each front contract (see ``calendar.expiry_dates``).
    roll_days : trading days before expiry at which the position rolls to rank 2.
    """
    ranks = held_rank(prices.index, expiries, roll_days)
    px = prices[[f"c{i}" for i in range(1, prices.shape[1] + 1)]].to_numpy(dtype=float)

    # first trading day after each expiry: every contract's rank shifts down by one
    after_expiry = pd.Series(prices.index, index=prices.index).shift(1).isin(expiries).to_numpy()

    prev_rank = ranks.shift(1).to_numpy()
    out = np.full(len(prices), np.nan)
    for t in range(1, len(prices)):
        r = int(prev_rank[t])
        r_today = r - 1 if after_expiry[t] else r
        if r_today < 1 or r > px.shape[1]:
            continue
        p_prev, p_now = px[t - 1, r - 1], px[t, r_today - 1]
        if p_prev > 0 and np.isfinite(p_now):
            out[t] = p_now / p_prev - 1.0
    return pd.Series(out, index=prices.index, name="ret")

