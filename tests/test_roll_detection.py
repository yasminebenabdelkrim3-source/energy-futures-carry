import numpy as np
import pandas as pd

from efc.data.roll_detection import label_shift_score, refine_expiries, roll_diagnostics


def _after(prices, expiries):
    return prices.index[pd.Series(prices.index).shift(1).isin(expiries).to_numpy()]


def test_score_spikes_on_label_shift_days(market):
    prices, expiries, *_ = market
    score = label_shift_score(prices)
    after = _after(prices, expiries)
    assert score.loc[after].min() > 1.5
    assert score.loc[after].median() > 5
    assert score.drop(after).median() < 1.5


def test_correct_calendar_is_confirmed(market):
    prices, expiries, *_ = market
    diag = roll_diagnostics(prices, expiries)
    assert (diag["status"] == "confirmed").all()


def test_refine_recovers_misaligned_expiries(market):
    prices, expiries, *_ = market
    idx = prices.index
    wrong = pd.DatetimeIndex(
        [idx[idx.get_loc(e) - 3] if k % 4 == 0 else e for k, e in enumerate(expiries)]
    )
    diag = roll_diagnostics(prices, wrong)
    assert (diag["status"] == "misaligned").sum() == int(np.ceil(len(expiries) / 4))
    pd.testing.assert_index_equal(refine_expiries(prices, wrong), expiries)


def test_flat_curve_is_inconclusive_and_kept():
    idx = pd.bdate_range("2024-01-01", periods=60)
    flat = pd.DataFrame({f"c{r}": 50.0 for r in range(1, 5)}, index=idx)
    flat = flat.mul(np.exp(np.linspace(0, 0.1, 60)), axis=0)
    exp = pd.DatetimeIndex([idx[20], idx[41]])
    diag = roll_diagnostics(flat, exp)
    assert (diag["status"] == "inconclusive").all()
    pd.testing.assert_index_equal(refine_expiries(flat, exp), exp)
