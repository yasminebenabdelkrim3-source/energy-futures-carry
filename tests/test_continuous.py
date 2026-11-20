import numpy as np
import pandas as pd
import pytest

from efc.data.continuous import held_rank, rolled_returns


def test_held_rank_window(market):
    prices, expiries, *_ = market
    ranks = held_rank(prices.index, expiries, roll_days=5)
    e = expiries[3]
    pos = prices.index.get_loc(e)
    assert (ranks.iloc[pos - 4 : pos + 1] == 2).all()
    assert ranks.iloc[pos - 5] == 1
    assert ranks.iloc[pos + 1] == 1


def test_roll_days_must_be_positive(market):
    prices, expiries, *_ = market
    with pytest.raises(ValueError):
        held_rank(prices.index, expiries, roll_days=0)


def test_rolled_returns_match_physical_contract(market):
    """The rolled series must equal the true return of the physical contract held."""
    prices, expiries, paths, front = market
    ranks = held_rank(prices.index, expiries, roll_days=5).to_numpy()
    ret = rolled_returns(prices, expiries, roll_days=5).to_numpy()

    for t in range(1, len(prices)):
        k = front[t - 1] + ranks[t - 1] - 1  # physical contract held at close t-1
        expected = paths[t, k] / paths[t - 1, k] - 1
        assert ret[t] == pytest.approx(expected, rel=1e-12), prices.index[t]


def test_naive_c1_returns_are_wrong_on_roll_days(market):
    """Sanity check that the problem we solve is real: c1.pct_change jumps at rolls."""
    prices, expiries, *_ = market
    naive = prices["c1"].pct_change()
    rolled = rolled_returns(prices, expiries)
    after = prices.index[pd.Series(prices.index).shift(1).isin(expiries).to_numpy()]
    assert (naive.loc[after] - rolled.loc[after]).abs().mean() > 1e-3


def test_negative_prices_do_not_break_returns(market):
    prices, expiries, *_ = market
    prices = prices.copy()
    e = expiries[5]
    prices.loc[e, "c1"] = -37.63  # WTI April 2020 style
    ret = rolled_returns(prices, expiries, roll_days=5)
    assert np.isfinite(ret.dropna()).all()
    # we were holding c2 on expiry day, so the negative c1 never enters returns
    assert ret.loc[e] == pytest.approx(prices.loc[e, "c2"] / prices["c2"].shift(1).loc[e] - 1)

