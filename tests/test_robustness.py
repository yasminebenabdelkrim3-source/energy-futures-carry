import numpy as np
import pandas as pd
import pytest

from efc.robustness import bootstrap_sharpe
from efc.signals.carry import seasonal_adjusted_carry

DAYS = pd.bdate_range("2000-01-01", "2012-12-31")


def test_seasonal_pattern_is_removed_but_level_kept():
    seasonal = 0.5 * np.cos(2 * np.pi * (DAYS.month - 1) / 12)
    carry = pd.Series(-0.1 + seasonal, index=DAYS)
    sa = seasonal_adjusted_carry(carry, min_years=3)
    assert sa.loc[:"2002"].isna().all()  # not enough history yet
    late = sa.loc["2004":]
    assert late.std() < 1e-9  # seasonal wave gone
    assert late.mean() == pytest.approx(-0.1)  # average carry level preserved


def test_seasonal_adjustment_uses_past_years_only():
    carry = pd.Series(0.0, index=DAYS)
    base = seasonal_adjusted_carry(carry)
    shocked = carry.copy()
    shocked.loc["2010-03"] = 5.0  # a huge March 2010
    sa = seasonal_adjusted_carry(shocked)
    pd.testing.assert_series_equal(sa.loc[:"2010-02"], base.loc[:"2010-02"])
    # the 2010 shock only affects adjustments from 2011 onwards
    assert (sa.loc["2010-04":"2010-12"] == base.loc["2010-04":"2010-12"]).all()
    assert sa.loc["2011-03"].mean() != base.loc["2011-03"].mean()


def test_bootstrap_detects_a_real_edge_and_rejects_noise():
    rng = np.random.default_rng(1)
    n = 252 * 20
    edge = pd.Series(rng.normal(0.0008, 0.01, n))  # Sharpe ~ 1.27
    noise = pd.Series(rng.normal(0.0, 0.01, n))
    b_edge = bootstrap_sharpe(edge, n_boot=500)
    b_noise = bootstrap_sharpe(noise, n_boot=500)
    assert b_edge["p-value (Sharpe<=0)"] < 0.01
    assert b_edge["CI low"] > 0
    assert b_noise["p-value (Sharpe<=0)"] > 0.05
    assert b_noise["CI low"] < 0 < b_noise["CI high"]


def test_bootstrap_rejects_short_series():
    with pytest.raises(ValueError):
        bootstrap_sharpe(pd.Series(np.zeros(50)), block=63)
