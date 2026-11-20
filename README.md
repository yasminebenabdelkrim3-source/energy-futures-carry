# Energy Futures Carry

[![CI](https://github.com/yasminebenabdelkrim3-source/energy-futures-carry/actions/workflows/ci.yml/badge.svg)](https://github.com/yasminebenabdelkrim3-source/energy-futures-carry/actions/workflows/ci.yml)

**Does the shape of the futures curve predict returns in energy markets?**
This project tests whether *carry* (the roll yield implied by backwardation or
contango) earns a risk premium across NYMEX energy futures, how it interacts
with time-series momentum, and how robust the result is across regimes:
the 2008 crash, the 2014–16 oil glut, negative WTI in April 2020, and the
2022 energy crisis.

> Status: **work in progress**. Data pipeline and carry signal are in place.
> The backtest and the research write-up come next (see [Roadmap](#roadmap)).

---

## Universe and data

| Key           | Contract                          | Unit       | Last trading day rule                         |
|---------------|-----------------------------------|------------|-----------------------------------------------|
| `wti`         | WTI Crude Oil (CL)                | USD/bbl    | 3 bdays before the 25th of the prior month    |
| `natgas`      | Henry Hub Natural Gas (NG)        | USD/MMBtu  | 3 bdays before the 1st of the delivery month  |
| `rbob`        | RBOB Gasoline (RB)                | USD/gal    | last bday of the prior month                  |
| `heating_oil` | NY Harbor ULSD / Heating Oil (HO) | USD/gal    | last bday of the prior month                  |

Daily settlement prices for contracts 1 to 4 come from the
[EIA open-data API](https://www.eia.gov/opendata/) (free key). Business days
are inferred from the data, so exchange holidays need no separate calendar.

## Methodology

### 1. From "contract 1" labels to tradable returns
EIA's *contract 1* is a label: the day after expiry, the old contract 2 becomes
contract 1. `c1.pct_change()` therefore mixes two contracts on roll days and
creates fake jumps equal to the calendar spread. That bias is large for natural gas.

`efc.data.continuous.rolled_returns` simulates a position that holds the front
contract, **rolls to the second contract N trading days before expiry**, and
measures every daily return on the *same physical contract*. The position never
holds a contract on its last trading day, which also avoids the delivery
squeeze of 20 April 2020 (WTI at −37 USD/bbl).

A built-in diagnostic (`roll_jump_diagnostics`) checks the inferred expiry
calendar against the data. On a true roll day, today's `c1` should be close to
yesterday's `c2`.

### 2. Carry signal
$$
\text{carry}_t = \frac{12}{m}\,\ln\frac{F^{\text{near}}_t}{F^{\text{far}}_t}
$$
Positive carry means backwardation and negative carry means contango. Inside the
roll window the signal uses the c2/c3 spread, i.e. the contract actually held.

### 3. Next: portfolio construction and evaluation
Cross-sectional and time-series carry, time-series momentum, and a combined
signal; volatility-scaled positions; transaction costs; walk-forward evaluation;
Sharpe ratio, drawdowns, turnover, VaR/ES; sub-period and parameter robustness.

## Quick start

```bash
git clone https://github.com/yasminebenabdelkrim3-source/energy-futures-carry
cd energy-futures-carry
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env        # then paste your free EIA API key
python scripts/download_data.py
pytest
```

```python
from efc.config import COMMODITIES
from efc.data import load_prices, expiry_dates, held_rank, rolled_returns
from efc.signals import carry_for_held

px = load_prices("wti")
exp = expiry_dates(px.index, COMMODITIES["wti"].expiry_rule)
ret = rolled_returns(px, exp, roll_days=5)
carry = carry_for_held(px, held_rank(px.index, exp, roll_days=5))
```

## Project layout

```
src/efc/
  config.py            commodity universe, EIA series ids, expiry rules
  data/eia.py          EIA API client with pagination + local CSV cache
  data/calendar.py     last-trading-day rules per contract
  data/continuous.py   rolled front-month returns + calendar diagnostics
  signals/carry.py     annualised carry from the term structure
scripts/download_data.py
tests/                 unit tests on a synthetic market with known ground truth
```

## Roadmap
- [x] Data pipeline (EIA, cache, expiry calendar, rolled returns)
- [x] Carry signal
- [ ] Momentum signals and signal combination
- [ ] Backtest engine (vol targeting, transaction costs, no look-ahead)
- [ ] Risk and performance analytics (Sharpe, drawdown, VaR/ES, turnover)
- [ ] Robustness: sub-periods, roll-day and lookback sensitivity
- [ ] Research notebook and write-up of findings

## Limitations
- EIA publishes only 4 contracts, so the seasonal shape of the natural gas curve
  (winter premium) contaminates the 1-to-2 month carry. A seasonally adjusted
  carry is planned.
- The universe is small (4 energy contracts). Cross-sectional results should be
  read with that in mind.
- Settlement prices only: no intraday data and no bid/ask. Costs are modelled
  as a fixed fee per roll and per rebalance.

## References
- Koijen, Moskowitz, Pedersen & Vrugt (2018), *Carry*, Journal of Financial Economics.
- Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*, Journal of Financial Economics.
- Erb & Harvey (2006), *The Strategic and Tactical Value of Commodity Futures*, Financial Analysts Journal.

---
*Research project for educational purposes. Not investment advice.*
