"""Performance and risk statistics for daily return series."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def drawdown(returns: pd.Series) -> pd.Series:
    """Drawdown of the compounded wealth curve, as a fraction of the running peak."""
    wealth = (1 + returns.fillna(0)).cumprod()
    return wealth / wealth.cummax() - 1


def historical_var_es(returns: pd.Series, level: float = 0.99) -> tuple[float, float]:
    """One-day historical VaR and Expected Shortfall, reported as positive losses."""
    r = returns.dropna()
    if r.empty:
        return np.nan, np.nan
    q = r.quantile(1 - level)
    return -q, -r[r <= q].mean()


def performance_summary(returns: pd.Series, turnover: pd.Series | None = None) -> dict:
    r = returns.dropna()
    if len(r) < 2:
        return {}
    years = len(r) / TRADING_DAYS
    ann_ret = (1 + r).prod() ** (1 / years) - 1
    ann_vol = r.std() * np.sqrt(TRADING_DAYS)
    downside = r[r < 0].std() * np.sqrt(TRADING_DAYS)
    mdd = drawdown(r).min()
    var99, es99 = historical_var_es(r)
    out = {
        "Ann. return": ann_ret,
        "Ann. vol": ann_vol,
        "Sharpe": r.mean() / r.std() * np.sqrt(TRADING_DAYS) if r.std() > 0 else np.nan,
        "Sortino": r.mean() * TRADING_DAYS / downside if downside > 0 else np.nan,
        "Max drawdown": mdd,
        "Calmar": ann_ret / -mdd if mdd < 0 else np.nan,
        "Skew": r.skew(),
        "VaR 99% (1d)": var99,
        "ES 99% (1d)": es99,
        "Hit rate": (r > 0).mean(),
    }
    if turnover is not None:
        out["Turnover / yr"] = turnover.reindex(r.index).sum() / years
    return out


def sharpe_by_period(returns: pd.Series, periods: dict[str, tuple[str, str]]) -> pd.Series:
    out = {}
    for name, (start, end) in periods.items():
        r = returns.loc[start:end].dropna()
        out[name] = r.mean() / r.std() * np.sqrt(TRADING_DAYS) if len(r) > 20 else np.nan
    return pd.Series(out)
