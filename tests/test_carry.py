import numpy as np
import pandas as pd
import pytest

from efc.signals.carry import annualized_carry, carry_for_held


def _panel(c1, c2, c3=None):
    idx = pd.bdate_range("2024-01-01", periods=len(c1))
    d = {"c1": c1, "c2": c2}
    if c3 is not None:
        d["c3"] = c3
    return pd.DataFrame(d, index=idx)


def test_backwardation_positive_contango_negative():
    p = _panel([100.0, 100.0], [99.0, 101.0])
    c = annualized_carry(p)
    assert c.iloc[0] > 0  # backwardation
    assert c.iloc[1] < 0  # contango
    assert c.iloc[0] == pytest.approx(np.log(100 / 99) * 12)


def test_months_apart_scaling():
    p = _panel([100.0], [98.0], [96.0])
    assert annualized_carry(p, 1, 3).iloc[0] == pytest.approx(np.log(100 / 96) * 6)


def test_non_positive_prices_give_nan():
    p = _panel([-37.0, 0.0, 20.0], [10.0, 10.0, 21.0])
    c = annualized_carry(p)
    assert c.iloc[:2].isna().all() and np.isfinite(c.iloc[2])


def test_far_must_follow_near():
    with pytest.raises(ValueError):
        annualized_carry(_panel([1.0], [1.0]), 2, 1)


def test_carry_for_held_uses_c2_c3_in_roll_window():
    p = _panel([100.0, 100.0], [99.0, 99.0], [95.0, 95.0])
    ranks = pd.Series([1, 2], index=p.index)
    c = carry_for_held(p, ranks)
    assert c.iloc[0] == pytest.approx(np.log(100 / 99) * 12)
    assert c.iloc[1] == pytest.approx(np.log(99 / 95) * 12)
