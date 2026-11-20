"""Carry (roll yield) implied by the futures term structure.

For two adjacent monthly contracts with prices F_near and F_far:

    carry = ln(F_near / F_far) * 12 / months_apart

Positive carry = backwardation (the curve slopes down): a long position earns the
roll yield as the far contract converges towards the near one, all else equal.
Negative carry = contango.

The signal is only defined when both prices are strictly positive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def annualized_carry(
    prices: pd.DataFrame, near: int = 1, far: int = 2, months_apart: int | None = None
) -> pd.Series:
    if far <= near:
        raise ValueError("far must be a later contract than near")
    months = months_apart if months_apart is not None else far - near
    f_near, f_far = prices[f"c{near}"], prices[f"c{far}"]
    valid = (f_near > 0) & (f_far > 0)
    carry = pd.Series(np.nan, index=prices.index, name="carry")
    carry[valid] = np.log(f_near[valid] / f_far[valid]) * 12.0 / months
    return carry


def carry_for_held(prices: pd.DataFrame, ranks: pd.Series) -> pd.Series:
    """Carry measured on the contract actually held (rank r vs r+1).

    Inside the roll window the position holds contract 2, so its relevant roll
    yield is the c2/c3 spread rather than c1/c2.
    """
    c12 = annualized_carry(prices, 1, 2)
    c23 = annualized_carry(prices, 2, 3) if "c3" in prices else c12
    out = c12.where(ranks.reindex(prices.index) == 1, c23)
    return out.rename("carry")


def seasonal_adjusted_carry(carry: pd.Series, min_years: int = 3) -> pd.Series:
    """Remove the average seasonal pattern of carry, using past years only.

    Natural gas is in steep contango every autumn (cheap October gas vs expensive
    winter gas) and in backwardation every late winter. That pattern is
    predictable and says nothing about supply and demand *this* year. We estimate,
    for each calendar month, how much carry typically deviates from its overall
    average, and subtract that seasonal component:

        adjusted_t = carry_t - (mean_past[carry | month(t)] - mean_past[carry])

    "past" means calendar years strictly before the year of t, so no information
    from the current year leaks into the adjustment. The first ``min_years`` years
    are NaN (not enough history).
    """
    s = carry.dropna()
    if s.empty:
        return carry.copy()
    monthly = s.groupby([s.index.year, s.index.month]).mean()
    monthly.index.names = ["year", "month"]
    table = monthly.unstack("month")  # rows: years, cols: calendar months

    # expanding means over strictly earlier years
    past_month_mean = table.expanding().mean().shift(1)
    past_count = table.notna().cumsum().shift(1)
    past_overall = table.stack().groupby(level=0).mean().expanding().mean().shift(1)
    component = past_month_mean.sub(past_overall, axis=0).where(past_count >= min_years)

    lookup = component.stack()  # Series indexed by (year, month)
    keys = pd.MultiIndex.from_arrays([carry.index.year, carry.index.month])
    values = lookup.reindex(keys).to_numpy(dtype=float)
    return (carry - values).rename("carry_sa")
