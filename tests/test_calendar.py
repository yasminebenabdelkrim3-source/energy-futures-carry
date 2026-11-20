import pandas as pd

from efc.data.calendar import expiry_dates


def test_wti_three_bdays_before_25th():
    # Nov 2026: the 25th is a Wednesday -> 3 business days before = Fri 20 Nov
    days = pd.bdate_range("2026-11-01", "2026-12-31")
    exp = expiry_dates(days, "wti")
    assert pd.Timestamp("2026-11-20") in exp


def test_wti_four_bdays_when_25th_not_a_business_day():
    # Oct 2026: the 25th is a Sunday -> 4 business days before = Tue 20 Oct
    days = pd.bdate_range("2026-10-01", "2026-11-30")
    exp = expiry_dates(days, "wti")
    assert pd.Timestamp("2026-10-20") in exp


def test_henry_hub_three_bdays_before_month_start():
    # Delivery Dec 2026 -> 3 business days before Tue 1 Dec = Thu 26 Nov
    days = pd.bdate_range("2026-11-01", "2026-12-31")
    exp = expiry_dates(days, "henry_hub")
    assert pd.Timestamp("2026-11-26") in exp


def test_holiday_taken_from_data():
    # Remove Thanksgiving (26 Nov 2026): NG expiry moves one day earlier
    days = pd.bdate_range("2026-11-01", "2026-12-31").drop(pd.Timestamp("2026-11-26"))
    exp = expiry_dates(days, "henry_hub")
    assert pd.Timestamp("2026-11-25") in exp


def test_last_bday_prior_month():
    days = pd.bdate_range("2026-10-01", "2026-12-15")
    exp = expiry_dates(days, "last_bday_prior_month")
    assert list(exp) == [pd.Timestamp("2026-10-30"), pd.Timestamp("2026-11-30")]


def test_incomplete_last_month_is_skipped():
    # data stops on 10 Nov: no November expiry can be inferred yet
    days = pd.bdate_range("2026-09-01", "2026-11-10")
    for rule in ("wti", "henry_hub", "last_bday_prior_month"):
        exp = expiry_dates(days, rule)
        assert all(d.month != 11 for d in exp), rule


def test_one_expiry_per_month():
    days = pd.bdate_range("2010-01-01", "2020-12-31")
    for rule in ("wti", "henry_hub", "last_bday_prior_month"):
        exp = expiry_dates(days, rule)
        assert exp.to_period("M").is_unique
        assert len(exp) >= 131
