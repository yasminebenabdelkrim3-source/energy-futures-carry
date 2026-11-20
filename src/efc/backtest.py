"""Vectorised backtest with explicit timing and transaction costs.

Timing: weights decided at the close of day t are held over day t+1, so the
return of day t+1 is ``sum_i w_i,t * r_i,t+1``. A signal can never see the
return it is paid on.

Costs (in basis points of notional traded, per side):
- rebalancing: ``|w_t - w_t-1|`` on rebalance days;
- rolling: closing the old contract and opening the new one, ``2 * |w_t|`` on
  each roll day.
Weight drift between rebalances is ignored (constant-weight approximation).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class BacktestResult:
    net: pd.Series
    gross: pd.Series
    costs: pd.Series
    weights: pd.DataFrame  # weights held at the close of each day
    turnover: pd.Series  # notional traded each day, as a fraction of capital


def run_backtest(
    returns: pd.DataFrame,
    target_weights: pd.DataFrame,
    rolls: pd.DataFrame | None = None,
    cost_bps: float = 5.0,
) -> BacktestResult:
    """Simulate a portfolio of futures.

    Parameters
    ----------
    returns : daily excess returns per asset.
    target_weights : weights on rebalance dates (other dates absent or NaN).
    rolls : boolean panel, True on the close where an asset's position rolls.
    cost_bps : one-way cost per unit of notional traded.
    """
    idx = returns.index
    w = target_weights.reindex(index=idx, columns=returns.columns).ffill().fillna(0.0)

    gross = (w.shift(1).fillna(0.0) * returns.fillna(0.0)).sum(axis=1)

    trades = w.diff().abs()
    trades.iloc[0] = w.iloc[0].abs()
    if rolls is not None:
        r = rolls.reindex(index=idx, columns=returns.columns).fillna(False).astype(bool)
        trades = trades + 2 * w.abs().where(r, 0.0)
    turnover = trades.sum(axis=1)
    costs = turnover * cost_bps / 1e4

    return BacktestResult(
        net=(gross - costs).rename("net"),
        gross=gross.rename("gross"),
        costs=costs.rename("costs"),
        weights=w,
        turnover=turnover.rename("turnover"),
    )
