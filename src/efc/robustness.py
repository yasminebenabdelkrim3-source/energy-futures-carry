"""Is the Sharpe ratio real, and does it survive other reasonable choices?

1. **Block bootstrap.** Daily returns are autocorrelated and volatility clusters,
   so resampling single days would understate uncertainty. We resample blocks of
   consecutive days (moving-block bootstrap) to build
   - a 95% confidence interval for the Sharpe ratio, and
   - a one-sided p-value for H0: true Sharpe <= 0, by bootstrapping the
     *demeaned* returns (a world where the strategy has no edge) and counting how
     often luck alone produces a Sharpe at least as high as the one observed.
2. **Sensitivity.** Re-run a strategy while changing one parameter at a time.
   A real effect should not depend on one lucky setting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _sharpe(x: np.ndarray) -> np.ndarray:
    sd = x.std(axis=-1, ddof=1)
    return np.where(sd > 0, x.mean(axis=-1) / sd * np.sqrt(TRADING_DAYS), np.nan)


def _block_indices(n: int, block: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)
    return idx[:, :n]


def bootstrap_sharpe(
    returns: pd.Series,
    block: int = 63,
    n_boot: int = 2000,
    seed: int = 42,
    ci: float = 0.95,
) -> dict:
    """Moving-block bootstrap of the annualised Sharpe ratio."""
    r = returns.dropna().to_numpy()
    if len(r) < 2 * block:
        raise ValueError("series too short for the chosen block length")
    rng = np.random.default_rng(seed)
    idx = _block_indices(len(r), block, n_boot, rng)
    observed = float(_sharpe(r))
    boot = _sharpe(r[idx])
    null = _sharpe((r - r.mean())[idx])
    lo, hi = np.nanquantile(boot, [(1 - ci) / 2, 1 - (1 - ci) / 2])
    return {
        "Sharpe": observed,
        "CI low": float(lo),
        "CI high": float(hi),
        "p-value (Sharpe<=0)": float((np.sum(null >= observed) + 1) / (n_boot + 1)),
        "t-stat (iid)": observed * np.sqrt(len(r) / TRADING_DAYS),
    }
