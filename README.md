# Energy Futures Carry

[![CI](https://github.com/yasminebenabdelkrim3-source/energy-futures-carry/actions/workflows/ci.yml/badge.svg)](https://github.com/yasminebenabdelkrim3-source/energy-futures-carry/actions/workflows/ci.yml)

**Does the shape of the futures curve predict returns in energy markets?**
This project tests whether *carry* (the roll yield implied by backwardation or
contango) earns a risk premium across NYMEX energy futures, how it interacts
with time-series momentum, and how robust the result is across regimes:
the 2008 crash, the 2014–16 oil glut, negative WTI in April 2020, and the
2022 energy crisis.

> Status: **work in progress**. The data pipeline, signals, backtest engine and
> first results are in place. Robustness tests come next (see [Roadmap](#roadmap)).

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

| Key           | Sample                  | Trading days |
|---------------|-------------------------|-------------:|
| `wti`         | 1985-01-02 → 2024-04-05 | 9,865 |
| `natgas`      | 1994-01-13 → 2024-04-05 | 7,591 |
| `rbob`        | 2005-10-03 → 2024-04-05 | 4,651 |
| `heating_oil` | 1994-02-02 → 2024-04-05 | 7,566 |

EIA stopped publishing NYMEX futures prices after 5 April 2024, so the sample
ends there.

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

### 2. Checking the calendar against the data
Exchange rules have changed over time. For example, Henry Hub contracts
expired 6 business days before delivery in the mid-1990s, versus 3 today.
`efc.data.roll_detection` therefore checks every expiry against the prices.
On the day after an expiry, each label moves down one contract. Today's
c1..c3 then line up with yesterday's c2..c4, not with yesterday's c1..c3:

$$
\text{score}_t=\frac{\operatorname{std}_r\big(\ln c_{r,t}-\ln c_{r,t-1}\big)}{\operatorname{std}_r\big(\ln c_{r,t}-\ln c_{r+1,t-1}\big)}
$$

The common market move cancels out of both terms, so the test still works on
volatile days. Each expiry is labelled *confirmed*, *inconclusive* (flat curve)
or *misaligned*. `refine_expiries` moves an expiry only when the data are
unambiguous.

| Commodity   | Confirmed | Inconclusive | Misaligned (rule) | Misaligned (refined) |
|-------------|----------:|-------------:|------------------:|---------------------:|
| WTI         | 387 | 65 | 19 | 0 |
| Natural gas | 296 | 34 | 33 | 0 |
| RBOB        | 207 | 11 |  4 | 0 |
| Heating oil | 291 | 56 | 15 | 0 |

Most natural gas corrections fall in 1994–1997, matching the older expiry rule.
The largest remaining daily moves are real events (17 Jan 1991, 20–21 Apr 2020,
Mar 2022), not roll artefacts.

### 3. Carry signal
$$
\text{carry}_t = \frac{12}{m}\,\ln\frac{F^{\text{near}}_t}{F^{\text{far}}_t}
$$
Positive carry means backwardation and negative carry means contango. Inside the
roll window the signal uses the c2/c3 spread, i.e. the contract actually held.

### 4. Next: portfolio construction and evaluation
Cross-sectional and time-series carry, time-series momentum, and a combined
signal; volatility-scaled positions; transaction costs; walk-forward evaluation;
Sharpe ratio, drawdowns, turnover, VaR/ES; sub-period and parameter robustness.

## First results

Settings were fixed in advance from the literature, with nothing tuned on this
data: monthly rebalancing, 10% ex-ante volatility per asset (60-day EWMA),
leverage capped at 2x per asset, roll 5 trading days before expiry, 12-1 month
momentum, 21-day smoothed carry, and **5 bps per side** on every rebalance and
every roll. Sample: 1995-01 to 2024-04.

![Cumulative net returns](reports/figures/cumulative.png)

| Strategy | Sharpe | Ann. return | Ann. vol | Max DD | ES 99% (1d) | Cost drag / yr |
|---|---:|---:|---:|---:|---:|---:|
| Long only (equal risk) | 0.17 | 1.1% | 8.4% | −52.1% | 1.9% | 0.4% |
| **TS carry** | **0.23** | 1.2% | 6.3% | −20.6% | 1.5% | 0.4% |
| XS carry | −0.03 | −0.2% | 3.5% | −15.2% | 0.8% | 0.3% |
| TS momentum | 0.07 | 0.2% | 7.4% | −37.6% | 1.6% | 0.4% |
| Carry + momentum | 0.19 | 0.9% | 5.7% | −21.0% | 1.4% | 0.3% |

Full table and Sharpe ratios by sub-period: [`reports/results.md`](reports/results.md).

![Drawdowns](reports/figures/drawdowns.png)

**What this shows so far**
- **Time-series carry has the best risk-adjusted return and much smaller
  drawdowns than holding energy long.** It was positive in the 2008 H2 crash
  (Sharpe +2.4, while the long-only portfolio was −3.8): steep contango warned
  of oversupply before prices fell.
- **But the evidence is weak.** A Sharpe ratio of 0.23 over 29 years gives a
  t-statistic of about 1.2. On its own, that is not statistically significant.
- **Cross-sectional carry does not work in this universe.** With only 4 highly
  correlated contracts, and natural gas carry structurally negative because of
  its seasonal curve (median −16% a year), the ranking mostly says "short gas".
  That is a seasonal bet, not a carry bet.
- **Momentum is weak on energy alone** and loses in sharp reversals (2008 H2,
  2017–2019, 2020).
- **Costs cost about 0.3–0.4% a year**, mostly from monthly rolls. That is a large
  share of the gross premium.

These are honest first numbers, not a strategy to trade. The next steps aim to
make the conclusions robust.

## Quick start

```bash
git clone https://github.com/yasminebenabdelkrim3-source/energy-futures-carry
cd energy-futures-carry
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env        # then paste your free EIA API key
python scripts/download_data.py
python scripts/run_backtest.py     # writes reports/results.md and figures
pytest
```

```python
from efc.config import COMMODITIES
from efc.data import expiry_dates, held_rank, load_prices, refine_expiries, rolled_returns
from efc.signals import carry_for_held

px = load_prices("wti")
exp = refine_expiries(px, expiry_dates(px.index, COMMODITIES["wti"].expiry_rule))
ret = rolled_returns(px, exp, roll_days=5)
carry = carry_for_held(px, held_rank(px.index, exp, roll_days=5))
```

## Project layout

```
src/efc/
  config.py            commodity universe, EIA series ids, expiry rules
  data/eia.py          EIA API client with pagination + local CSV cache
  data/calendar.py     last-trading-day rules per contract
  data/continuous.py   rolled front-month returns
  data/roll_detection.py  data-driven check and refinement of the expiry calendar
  signals/carry.py     annualised carry from the term structure
  signals/momentum.py  time-series momentum (12-1)
  portfolio.py         panel building, EWMA vol, position sizing, strategies
  backtest.py          no-look-ahead engine with rebalance and roll costs
  metrics.py           Sharpe, Sortino, drawdowns, VaR / ES, sub-periods
scripts/download_data.py
scripts/run_backtest.py
reports/               results table and figures
tests/                 unit tests on a synthetic market with known ground truth
```

## Roadmap
- [x] Data pipeline (EIA, cache, expiry calendar, rolled returns)
- [x] Data-driven validation of the expiry calendar
- [x] Carry signal
- [x] Momentum signals and signal combination
- [x] Backtest engine (vol targeting, transaction costs, no look-ahead)
- [x] Risk and performance analytics (Sharpe, drawdown, VaR/ES, turnover)
- [ ] Seasonally adjusted carry for natural gas (and refined products)
- [ ] Statistical significance: block bootstrap of Sharpe ratios
- [ ] Robustness: roll-day, lookback, cost and rebalancing-frequency sensitivity
- [ ] Research notebook and write-up of findings

## Limitations
- The sample ends on 5 April 2024, when EIA stopped publishing futures prices.
  Extending it would need another data source.
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
