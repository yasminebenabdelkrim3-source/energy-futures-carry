"""From signals to positions: volatility scaling and the strategies tested.

Conventions
-----------
- ``weights`` are notional exposures as a fraction of capital (1.0 = one dollar
  of futures notional per dollar of capital), decided at the close of a
  rebalance day and held until the next one.
- Every asset is scaled to the same ex-ante volatility, so a 50%-vol natural gas
  position does not dominate a 30%-vol heating oil position.
- All parameters are fixed in advance from the literature (12-1 momentum,
  60-day EWMA half-life, monthly rebalancing). Nothing is tuned on the data;
  sensitivity to these choices is a separate robustness study.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from efc.config import COMMODITIES
from efc.data.calendar import expiry_dates
from efc.data.continuous import held_rank, rolled_returns
from efc.data.roll_detection import refine_expiries
from efc.signals.carry import carry_for_held
from efc.signals.momentum import tsmom_signal

TRADING_DAYS = 252


@dataclass
class Panel:
    """Aligned daily panels, one column per commodity."""

    returns: pd.DataFrame  # rolled excess returns
    carry: pd.DataFrame  # annualised carry of the contract held
    rolls: pd.DataFrame  # True on the close where the position rolls c1 -> c2


def build_panel(prices: dict[str, pd.DataFrame], roll_days: int = 5) -> Panel:
    rets, carry, rolls = {}, {}, {}
    for key, px in prices.items():
        exp = refine_expiries(px, expiry_dates(px.index, COMMODITIES[key].expiry_rule))
        ranks = held_rank(px.index, exp, roll_days)
        rets[key] = rolled_returns(px, exp, roll_days)
        carry[key] = carry_for_held(px, ranks)
        rolls[key] = ranks.diff().fillna(0) > 0
    returns = pd.DataFrame(rets).sort_index()
    return Panel(
        returns=returns,
        carry=pd.DataFrame(carry).reindex(returns.index),
        rolls=pd.DataFrame(rolls).reindex(returns.index).fillna(False).astype(bool),
    )


def ewma_vol(returns: pd.DataFrame, halflife: int = 60, min_periods: int = 60) -> pd.DataFrame:
    """Annualised exponentially weighted volatility, known at the close of each day."""
    return returns.ewm(halflife=halflife, min_periods=min_periods).std() * np.sqrt(TRADING_DAYS)


def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(index.to_period("M")).max().to_numpy())


def scale_positions(
    direction: pd.DataFrame,
    vol: pd.DataFrame,
    rebalance: pd.DatetimeIndex,
    target_vol: float = 0.10,
    max_leverage: float = 2.0,
) -> pd.DataFrame:
    """Turn directions in [-1, 1] into vol-scaled weights on rebalance dates.

    Each active asset gets ``direction * target_vol / vol / n_active``, capped at
    ``max_leverage`` in absolute value. Rows outside ``rebalance`` are NaN, so the
    backtest engine carries the last weights forward.
    """
    d = direction.reindex(rebalance)
    v = vol.reindex(rebalance)
    active = d.notna() & v.notna() & (v > 0)
    n_active = active.sum(axis=1).replace(0, np.nan)
    w = (d * target_vol / v).where(active).div(n_active, axis=0)
    return w.clip(-max_leverage, max_leverage).fillna(0.0)


def cross_sectional_rank(signal: pd.DataFrame) -> pd.DataFrame:
    """Demeaned ranks scaled to [-1, 1]: long the highest, short the lowest."""
    ranks = signal.rank(axis=1)
    centred = ranks.sub(ranks.mean(axis=1), axis=0)
    scale = centred.abs().max(axis=1).replace(0, np.nan)
    return centred.div(scale, axis=0)


def strategy_directions(panel: Panel, carry_smoothing: int = 21) -> dict[str, pd.DataFrame]:
    """Directions in [-1, 1] for each strategy, known at the close of each day."""
    carry = panel.carry.rolling(carry_smoothing, min_periods=carry_smoothing // 2).mean()
    mom = tsmom_signal(panel.returns)
    ts_carry = np.sign(carry)
    tsmom = np.sign(mom)
    return {
        "Long only": panel.returns.notna().astype(float).where(panel.returns.notna()),
        "TS carry": ts_carry,
        "XS carry": cross_sectional_rank(carry),
        "TS momentum": tsmom,
        "Carry + momentum": (ts_carry + tsmom) / 2,
    }
