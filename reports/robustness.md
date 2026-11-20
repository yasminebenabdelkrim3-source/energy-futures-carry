# Robustness

Baseline settings as in `results.md` (5 bps per side, monthly rebalancing, roll 5 days
before expiry, 21-day carry smoothing, 12-1 momentum). Net returns from 1995.

## 1. Is the Sharpe ratio different from zero?

Moving-block bootstrap, 63-day blocks, 2000 resamples. The p-value tests
H0: Sharpe <= 0 by resampling demeaned returns. Eight strategies are tested, so
individual p-values near 0.05 should be read with a multiple-testing discount.

| Strategy | Sharpe | CI low | CI high | p-value (Sharpe<=0) | t-stat (iid) |
|---|---:|---:|---:|---:|---:|
| Long only | 0.172 | -0.249 | 0.614 | 0.239 | 0.929 |
| TS carry | 0.226 | -0.155 | 0.572 | 0.098 | 1.221 |
| XS carry | -0.027 | -0.404 | 0.324 | 0.546 | -0.144 |
| TS momentum | 0.070 | -0.305 | 0.403 | 0.331 | 0.376 |
| Carry + momentum | 0.193 | -0.206 | 0.538 | 0.134 | 1.041 |
| TS carry SA | 0.297 | -0.075 | 0.660 | 0.068 | 1.607 |
| XS carry SA | 0.330 | -0.046 | 0.714 | 0.051 | 1.782 |
| Carry SA + momentum | 0.282 | -0.098 | 0.620 | 0.065 | 1.524 |

## 2. Split sample

| Strategy | 1995-2009 | 2010-2024 |
|---|---:|---:|
| Long only | 0.44 | -0.11 |
| TS carry | 0.35 | 0.06 |
| XS carry | 0.11 | -0.19 |
| TS momentum | 0.21 | -0.09 |
| Carry + momentum | 0.35 | 0.00 |
| TS carry SA | 0.40 | 0.17 |
| XS carry SA | 0.42 | 0.24 |
| Carry SA + momentum | 0.44 | 0.07 |

## 3. Sensitivity (Sharpe ratio, one parameter changed at a time)

### Roll (trading days before expiry)

| Strategy | 1d | 3d | 5d | 10d |
|---|---:|---:|---:|---:|
| TS carry | 0.26 | 0.23 | 0.23 | 0.27 |
| TS carry SA | 0.37 | 0.36 | 0.30 | 0.34 |
| XS carry SA | 0.31 | 0.27 | 0.33 | 0.33 |
| Carry SA + momentum | 0.39 | 0.34 | 0.28 | 0.32 |

### Cost (bps per side)

| Strategy | 0 | 2.5 | 5 | 10 | 20 |
|---|---:|---:|---:|---:|---:|
| TS carry | 0.29 | 0.26 | 0.23 | 0.16 | 0.04 |
| TS carry SA | 0.36 | 0.33 | 0.30 | 0.24 | 0.12 |
| XS carry SA | 0.41 | 0.37 | 0.33 | 0.25 | 0.10 |
| Carry SA + momentum | 0.33 | 0.30 | 0.28 | 0.24 | 0.15 |

### Carry smoothing (days)

| Strategy | 1d | 5d | 21d | 63d |
|---|---:|---:|---:|---:|
| TS carry | 0.13 | 0.16 | 0.23 | 0.16 |
| TS carry SA | 0.18 | 0.21 | 0.30 | 0.17 |
| XS carry SA | 0.08 | -0.02 | 0.33 | 0.40 |
| Carry SA + momentum | 0.21 | 0.23 | 0.28 | 0.20 |

### Momentum lookback (days)

| Strategy | 63d | 126d | 252d |
|---|---:|---:|---:|
| TS carry | 0.23 | 0.23 | 0.23 |
| TS carry SA | 0.30 | 0.30 | 0.30 |
| XS carry SA | 0.33 | 0.33 | 0.33 |
| Carry SA + momentum | 0.20 | 0.33 | 0.28 |
