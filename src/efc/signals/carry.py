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
