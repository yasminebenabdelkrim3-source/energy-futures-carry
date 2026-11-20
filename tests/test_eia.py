"""EIA client tests with a fake HTTP session (no network, no API key needed)."""

import pandas as pd
import pytest

from efc.data import eia


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.text = payload, status, str(payload)

    def json(self):
        return self._payload


class FakeSession:
    """Serves 7 rows in pages of 3 to exercise pagination."""

    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def get(self, url, params, timeout):
        self.calls.append(params)
        off, length = params["offset"], min(params["length"], 3)
        page = self.rows[off : off + length]
        return FakeResponse({"response": {"total": len(self.rows), "data": page}})


ROWS = [{"period": f"2024-01-0{i}", "value": str(70 + i)} for i in range(1, 8)]


def test_fetch_series_paginates_and_parses():
    s = eia.fetch_series("PET.RCLC1.D", api_key="k", session=FakeSession(ROWS))
    assert len(s) == 7
    assert s.index.is_monotonic_increasing
    assert s.iloc[0] == 71.0 and s.dtype == float


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    with pytest.raises(eia.EIAError, match="API key"):
        eia.fetch_series("PET.RCLC1.D", session=FakeSession(ROWS))


def test_http_error_raises():
    class Bad(FakeSession):
        def get(self, url, params, timeout):
            return FakeResponse({}, status=403)

    with pytest.raises(eia.EIAError, match="403"):
        eia.fetch_series("X", api_key="k", session=Bad([]))


def test_load_prices_uses_cache(tmp_path):
    df = pd.DataFrame(
        {"c1": [1.0, 2.0], "c2": [1.1, 2.1]},
        index=pd.DatetimeIndex(["2024-01-02", "2024-01-03"], name="date"),
    )
    df.to_csv(tmp_path / "wti.csv")
    out = eia.load_prices("wti", data_dir=tmp_path)
    pd.testing.assert_frame_equal(out, df, check_freq=False)


def test_unknown_commodity():
    with pytest.raises(KeyError):
        eia.load_prices("bitcoin")
