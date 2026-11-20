"""Synthetic futures market with a known ground truth.

We simulate one price path per *physical* contract, then label them c1..c4 by
rank exactly the way EIA does. Any correct rolling logic must recover the true
returns of the physical contracts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from efc.data.calendar import expiry_dates


def make_market(
    rule: str = "wti", start: str = "2019-01-01", end: str = "2021-12-31", seed: int = 0
):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end)
    expiries = expiry_dates(days, rule)

    # physical contract k expires at expiries[k]; we need 4 alive at any time
    n_contracts = len(expiries) + 4
    # each contract: independent-ish GBM around a curve level with a fixed spread
    common = np.cumsum(rng.normal(0, 0.02, len(days)))
    paths = np.empty((len(days), n_contracts))
    for k in range(n_contracts):
        idio = np.cumsum(rng.normal(0, 0.005, len(days)))
        paths[:, k] = 60.0 * np.exp(common + idio - 0.01 * k)

    # front physical contract on each day = number of expiries strictly before that day
    front = np.searchsorted(expiries.values, days.values, side="left")
    prices = pd.DataFrame(
        {f"c{r}": paths[np.arange(len(days)), front + r - 1] for r in range(1, 5)},
        index=days,
    )
    prices.index.name = "date"
    return prices, expiries, paths, front


@pytest.fixture
def market():
    return make_market()
