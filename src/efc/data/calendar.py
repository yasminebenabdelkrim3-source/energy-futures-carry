"""Last-trading-day rules for monthly NYMEX energy contracts.

The set of business days is taken from the price data itself (days with a
settlement), so exchange holidays are handled without a holiday calendar.

Rules (CME contract specs):
- ``wti`` (CL): trading ends 3 business days before the 25th calendar day of the
  month prior to delivery; 4 business days before if the 25th is not a business day.
- ``henry_hub`` (NG): 3 business days before the first calendar day of the
  delivery month.
- ``last_bday_prior_month`` (RB, HO): last business day of the month prior to
  delivery.

All contracts are monthly, so exactly one front contract expires per calendar
month. The function returns that expiry date for every month covered by the data.
"""

from __future__ import annotations

import pandas as pd

from efc.config import ExpiryRule


def _nth_trading_day_before(days: pd.DatetimeIndex, anchor: pd.Timestamp, n: int) -> pd.Timestamp:
    before = days[days < anchor]
    if len(before) < n:
        return pd.NaT
    return before[-n]


def expiry_dates(trading_days: pd.DatetimeIndex, rule: ExpiryRule) -> pd.DatetimeIndex:
    days = pd.DatetimeIndex(trading_days).normalize().unique().sort_values()
    if days.empty:
        return pd.DatetimeIndex([])

    months = pd.period_range(days[0], days[-1], freq="M")
    out: list[pd.Timestamp] = []
    for m in months:
        if rule == "wti":
            anchor = pd.Timestamp(year=m.year, month=m.month, day=25)
            n = 3 if anchor in days else 4
        elif rule == "henry_hub":
            anchor = (m + 1).to_timestamp()  # 1st day of delivery month
            n = 3
        elif rule == "last_bday_prior_month":
            anchor = (m + 1).to_timestamp()
            n = 1
        else:  # pragma: no cover - guarded by the Literal type
            raise ValueError(f"unknown expiry rule {rule!r}")

        # the data must extend past the anchor, otherwise the month is incomplete
        # and "n days before the anchor" would point to the wrong day
        if days[-1] < anchor:
            continue
        exp = _nth_trading_day_before(days, anchor, n)
        if pd.notna(exp) and exp.to_period("M") == m:
            out.append(exp)
    return pd.DatetimeIndex(out)
