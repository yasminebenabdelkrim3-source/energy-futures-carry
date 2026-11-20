"""Time-series momentum (Moskowitz, Ooi & Pedersen, 2012).

The signal is the cumulative log return of the rolled futures position over the
past ``lookback`` trading days, skipping the most recent ``skip`` days (the
classic "12-1": 12 months excluding the last one, which tends to mean-revert).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def tsmom_signal(
    returns: pd.Series | pd.DataFrame, lookback: int = 252, skip: int = 21
) -> pd.Series | pd.DataFrame:
    """Past cumulative log return from t-lookback to t-skip, known at the close of t."""
    if not 0 <= skip < lookback:
        raise ValueError("need 0 <= skip < lookback")
    window = lookback - skip
    logr = np.log1p(returns)
    cum = logr.rolling(window, min_periods=int(0.8 * window)).sum()
    return cum.shift(skip)
