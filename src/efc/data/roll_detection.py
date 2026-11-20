"""Detect, from the prices themselves, the day EIA's contract labels shift.

Idea: on an ordinary day, each label keeps the same physical contract, so the
daily log-returns of c1, c2, c3 are all close to the common market move. On the
day after an expiry every label moves one contract down (today's c1 is
yesterday's c2, ...). Comparing today's c1..c3 with yesterday's *same* labels then
mixes different contracts and the cross-rank dispersion of "returns" jumps,
while comparing them with yesterday's c2..c4 gives a tight, coherent move.

    score_t = std_rank( ln c_r,t - ln c_r,t-1 ) / std_rank( ln c_r,t - ln c_r+1,t-1 )

score >> 1 means a label shift happened on day t. The common market move cancels
out of both dispersions, which makes the test robust to volatile days.

The rule-based calendar (``calendar.expiry_dates``) is the prior; this module
checks it and moves an expiry only when the data are unambiguous. That matters
because the rolled-return engine needs the day the *labels* shift, which is
what the data show, whatever the exchange rule was at the time (e.g. Henry Hub
contracts expired 6 business days before delivery in the mid-1990s).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_EPS = 1e-6


def label_shift_score(prices: pd.DataFrame) -> pd.Series:
    """Score of a label shift between t-1 and t (NaN on the first day)."""
    ranks = [c for c in ("c1", "c2", "c3", "c4") if c in prices]
    if len(ranks) < 3:
        raise ValueError("need at least contracts c1..c3 to detect label shifts")
    lp = np.log(prices[ranks].where(prices[ranks] > 0)).to_numpy()
    same = lp[1:, :-1] - lp[:-1, :-1]  # c_r,t vs c_r,t-1
    shifted = lp[1:, :-1] - lp[:-1, 1:]  # c_r,t vs c_r+1,t-1
    with np.errstate(invalid="ignore"):
        score = (np.nanstd(same, axis=1) + _EPS) / (np.nanstd(shifted, axis=1) + _EPS)
    return pd.Series(np.r_[np.nan, score], index=prices.index, name="shift_score")


def roll_diagnostics(
    prices: pd.DataFrame,
    expiries: pd.DatetimeIndex,
    window: int = 6,
    confirm: float = 1.5,
    strong: float = 5.0,
) -> pd.DataFrame:
    """Check each expiry against the data.

    For each expiry, look at the shift score on the following trading day and at
    the best score within +/- ``window`` trading days. Status:
    - ``confirmed``: the data show a shift on the expected day (score >= confirm)
    - ``misaligned``: no shift on the expected day, a clear one nearby (>= strong)
    - ``inconclusive``: flat curve, the data cannot tell (common in quiet markets)
    """
    score = label_shift_score(prices)
    idx = prices.index
    rows = []
    for e in expiries:
        i = idx.get_loc(e) + 1
        if i >= len(idx):
            continue
        at = score.iloc[i]
        lo, hi = max(1, i - window), min(len(idx) - 1, i + window)
        w = score.iloc[lo : hi + 1]
        best_pos = lo + int(np.nanargmax(w.to_numpy()))
        best = score.iloc[best_pos]
        if at >= confirm:
            status = "confirmed"
        elif best >= strong:
            status = "misaligned"
        else:
            status = "inconclusive"
        rows.append(
            {
                "expiry": e,
                "score_expected": at,
                "best_score": best,
                "best_offset": best_pos - i,
                "status": status,
            }
        )
    return pd.DataFrame(rows).set_index("expiry") if rows else pd.DataFrame()


def refine_expiries(
    prices: pd.DataFrame,
    expiries: pd.DatetimeIndex,
    window: int = 6,
    confirm: float = 1.5,
    strong: float = 5.0,
) -> pd.DatetimeIndex:
    """Move ``misaligned`` expiries to the day before the detected label shift.

    Confirmed and inconclusive expiries are kept as given by the exchange rule.
    """
    diag = roll_diagnostics(prices, expiries, window, confirm, strong)
    if diag.empty:
        return pd.DatetimeIndex(expiries)
    idx = prices.index
    out = []
    for e in expiries:
        if e in diag.index and diag.at[e, "status"] == "misaligned":
            shift_day = idx.get_loc(e) + 1 + int(diag.at[e, "best_offset"])
            out.append(idx[shift_day - 1])
        else:
            out.append(e)
    refined = pd.DatetimeIndex(out)
    # keep one expiry per month and strictly increasing dates
    return refined[~refined.duplicated()].sort_values()
