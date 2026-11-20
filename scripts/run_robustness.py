"""Statistical significance and parameter sensitivity of every strategy.

Usage:
    python scripts/run_robustness.py

Outputs:
    reports/robustness.md               bootstrap table, split-sample and sensitivity grids
    reports/figures/bootstrap_ci.png    Sharpe ratios with 95% bootstrap intervals
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from efc.backtest import run_backtest  # noqa: E402
from efc.config import COMMODITIES, PROJECT_ROOT  # noqa: E402
from efc.data.eia import load_prices  # noqa: E402
from efc.metrics import sharpe_by_period  # noqa: E402
from efc.portfolio import (  # noqa: E402
    build_panel,
    ewma_vol,
    month_end_dates,
    scale_positions,
    strategy_directions,
)
from efc.robustness import bootstrap_sharpe  # noqa: E402

REPORTS = PROJECT_ROOT / "reports"
START = "1995-01-01"
FOCUS = ["TS carry", "TS carry SA", "XS carry SA", "Carry SA + momentum"]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e6e5e0"
ACCENT, NEUTRAL = "#2a78d6", "#8a8a85"


def backtest_all(panel, cost_bps=5.0, **signal_kw) -> dict[str, pd.Series]:
    vol = ewma_vol(panel.returns)
    rebalance = month_end_dates(panel.returns.index)
    out = {}
    for name, direction in strategy_directions(panel, **signal_kw).items():
        w = scale_positions(direction, vol, rebalance)
        out[name] = run_backtest(panel.returns, w, panel.rolls, cost_bps=cost_bps).net.loc[START:]
    return out


def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    return r.mean() / r.std() * 252**0.5


def md_table(df: pd.DataFrame, fmt="{:.2f}", index_name="Strategy") -> str:
    cols = [str(c) for c in df.columns]
    lines = [f"| {index_name} | " + " | ".join(cols) + " |", "|---" + "|---:" * len(cols) + "|"]
    for name, row in df.iterrows():
        lines.append(f"| {name} | " + " | ".join(fmt.format(v) for v in row) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--n-boot", type=int, default=2000)
    args = parser.parse_args()

    kw = {"data_dir": args.data_dir} if args.data_dir else {}
    prices = {k: load_prices(k, **kw) for k in COMMODITIES}
    panel = build_panel(prices)

    # 1. bootstrap significance, baseline settings
    base = backtest_all(panel)
    boot = pd.DataFrame({n: bootstrap_sharpe(r, n_boot=args.n_boot) for n, r in base.items()}).T

    # 2. split sample: does the effect hold in both halves?
    halves = {"1995-2009": ("1995", "2009"), "2010-2024": ("2010", "2024")}
    split = pd.DataFrame({n: sharpe_by_period(r, halves) for n, r in base.items()}).T

    # 3. one-at-a-time sensitivity on the focus strategies
    grids = {}
    grids["Roll (trading days before expiry)"] = {
        f"{d}d": backtest_all(build_panel(prices, roll_days=d)) for d in (1, 3, 5, 10)
    }
    grids["Cost (bps per side)"] = {
        f"{c:g}": backtest_all(panel, cost_bps=c) for c in (0, 2.5, 5, 10, 20)
    }
    grids["Carry smoothing (days)"] = {
        f"{s}d": backtest_all(panel, carry_smoothing=s) for s in (1, 5, 21, 63)
    }
    grids["Momentum lookback (days)"] = {
        f"{lb}d": backtest_all(panel, mom_lookback=lb) for lb in (63, 126, 252)
    }
    sens = {
        title: pd.DataFrame({k: {n: sharpe(res[n]) for n in FOCUS} for k, res in g.items()})
        for title, g in grids.items()
    }

    print(boot.round(3).to_string(), "\n")
    print(split.round(2).to_string(), "\n")
    for title, df in sens.items():
        print(title)
        print(df.round(2).to_string(), "\n")

    # report
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "figures").mkdir(exist_ok=True)
    boot_fmt = boot.copy()
    md = [
        "# Robustness",
        "",
        "Baseline settings as in `results.md` (5 bps per side, monthly rebalancing, roll 5 days",
        "before expiry, 21-day carry smoothing, 12-1 momentum). Net returns from 1995.",
        "",
        "## 1. Is the Sharpe ratio different from zero?",
        "",
        f"Moving-block bootstrap, 63-day blocks, {args.n_boot} resamples. The p-value tests",
        "H0: Sharpe <= 0 by resampling demeaned returns. Eight strategies are tested, so",
        "individual p-values near 0.05 should be read with a multiple-testing discount.",
        "",
        md_table(boot_fmt, "{:.3f}"),
        "",
        "## 2. Split sample",
        "",
        md_table(split),
        "",
        "## 3. Sensitivity (Sharpe ratio, one parameter changed at a time)",
    ]
    for title, df in sens.items():
        md += ["", f"### {title}", "", md_table(df)]
    (REPORTS / "robustness.md").write_text("\n".join(md) + "\n")

    # figure: Sharpe with bootstrap CI, sorted
    b = boot.sort_values("Sharpe")
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    y = range(len(b))
    colors = [ACCENT if n in FOCUS[1:] else NEUTRAL for n in b.index]
    ax.hlines(y, b["CI low"], b["CI high"], colors=colors, lw=2)
    ax.scatter(b["Sharpe"], y, s=40, color=colors, zorder=3, edgecolor="white", linewidth=1.5)
    for yi, (_, row) in zip(y, b.iterrows(), strict=True):
        ax.annotate(
            f"{row['Sharpe']:.2f}  (p={row['p-value (Sharpe<=0)']:.2f})",
            (row["CI high"], yi), xytext=(6, 0), textcoords="offset points",
            va="center", fontsize=8, color=INK,
        )
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(list(y), b.index, color=INK, fontsize=9)
    ax.set_xlabel("Annualised Sharpe ratio, 95% block-bootstrap interval", color=MUTED)
    ax.set_title(
        "Seasonally adjusted carry (blue) vs other strategies", loc="left", color=INK, fontsize=12
    )
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_xlim(right=b["CI high"].max() + 0.45)
    fig.tight_layout()
    fig.savefig(REPORTS / "figures" / "bootstrap_ci.png")
    plt.close(fig)
    print(f"Wrote {REPORTS / 'robustness.md'} and figure.")


if __name__ == "__main__":
    main()
