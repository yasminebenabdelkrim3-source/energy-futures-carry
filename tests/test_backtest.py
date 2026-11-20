import numpy as np
import pandas as pd
import pytest

from efc.backtest import run_backtest
from efc.metrics import drawdown, historical_var_es, performance_summary
from efc.portfolio import cross_sectional_rank, month_end_dates, scale_positions
from efc.signals.momentum import tsmom_signal

IDX = pd.bdate_range("2020-01-01", periods=300)


def _returns(seed=0, n_assets=2):
    rng = np.random.default_rng(seed)
    data = rng.normal(0, 0.01, (len(IDX), n_assets))
    return pd.DataFrame(data, index=IDX, columns=list("ab")[:n_assets])


def test_no_look_ahead():
    """A 'perfect foresight' weight set on day t must not earn day t's return."""
    rets = _returns()
    cheat = np.sign(rets)  # knows today's return at today's close
    res = run_backtest(rets, cheat, cost_bps=0)
    # weights decided at t only earn r_{t+1}; with iid returns the edge vanishes
    assert abs(res.gross.mean()) < 0.002
    # and the engine does pay w_t * r_{t+1}
    expected = (cheat.shift(1).fillna(0) * rets).sum(axis=1)
    pd.testing.assert_series_equal(res.gross, expected, check_names=False)


def test_rebalance_and_roll_costs():
    rets = pd.DataFrame(0.0, index=IDX[:5], columns=["a"])
    w = pd.DataFrame({"a": [0.5, np.nan, 1.0, np.nan, np.nan]}, index=IDX[:5])
    rolls = pd.DataFrame({"a": [False, False, False, True, False]}, index=IDX[:5])
    res = run_backtest(rets, w, rolls, cost_bps=10)
    # day 0: open 0.5; day 2: +0.5; day 3: roll 2 * 1.0
    assert res.turnover.tolist() == pytest.approx([0.5, 0, 0.5, 2.0, 0])
    assert res.costs.sum() == pytest.approx(3.0 * 10 / 1e4)
    assert res.net.sum() == pytest.approx(-res.costs.sum())


def test_scale_positions_equal_risk_and_cap():
    rebal = IDX[[10, 20]]
    direction = pd.DataFrame({"a": 1.0, "b": -1.0}, index=IDX)
    vol = pd.DataFrame({"a": 0.20, "b": 0.01}, index=IDX)
    w = scale_positions(direction, vol, rebal, target_vol=0.10, max_leverage=2.0)
    assert list(w.index) == list(rebal)
    assert w["a"].iloc[0] == pytest.approx(0.10 / 0.20 / 2)
    assert w["b"].iloc[0] == pytest.approx(-2.0)  # 0.10/0.01/2 = 5 -> capped


def test_scale_positions_ignores_missing_assets():
    direction = pd.DataFrame({"a": 1.0, "b": np.nan}, index=IDX)
    vol = pd.DataFrame({"a": 0.10, "b": 0.10}, index=IDX)
    w = scale_positions(direction, vol, IDX[[5]], target_vol=0.10)
    assert w.loc[IDX[5], "a"] == pytest.approx(1.0)  # alone -> full risk budget
    assert w.loc[IDX[5], "b"] == 0.0


def test_cross_sectional_rank():
    sig = pd.DataFrame({"a": [3.0], "b": [1.0], "c": [2.0], "d": [np.nan]})
    r = cross_sectional_rank(sig).iloc[0]
    assert r["a"] == 1.0 and r["b"] == -1.0 and r["c"] == 0.0 and np.isnan(r["d"])


def test_tsmom_skips_recent_month():
    r = pd.Series(0.0, index=IDX)
    r.iloc[100] = 0.5
    sig = tsmom_signal(r, lookback=60, skip=21)
    assert sig.iloc[120] == pytest.approx(0.0)  # jump still inside the skipped month
    assert sig.iloc[121] == pytest.approx(np.log(1.5))  # now part of the signal
    assert sig.iloc[159] == pytest.approx(np.log(1.5))  # window is t-59..t-21
    assert sig.iloc[160] == pytest.approx(0.0)  # dropped out of the lookback


def test_month_end_dates():
    d = month_end_dates(IDX)
    assert d[0] == pd.Timestamp("2020-01-31")
    assert d.to_period("M").is_unique


def test_metrics_on_known_series():
    r = pd.Series([0.1, -0.5, 0.2], index=IDX[:3])
    dd = drawdown(r)
    assert dd.min() == pytest.approx(-0.5)
    var, es = historical_var_es(pd.Series(np.linspace(-0.1, 0.1, 201)), level=0.99)
    assert var == pytest.approx(0.098) and es == pytest.approx(0.099)
    s = performance_summary(_returns()["a"])
    assert {"Sharpe", "Max drawdown", "ES 99% (1d)"} <= set(s)
