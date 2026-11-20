"""Run every strategy on the cached EIA data and write the results.

Usage:
    python scripts/run_backtest.py                 # default settings
    python scripts/run_backtest.py --cost-bps 10   # stress the cost assumption

Outputs:
    reports/results.md                 performance table + sub-period Sharpe ratios
    reports/figures/cumulative.png     cumulative net returns (log scale)
    reports/figures/drawdowns.png      drawdowns, seasonally adjusted TS carry vs long only
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from efc.backtest import run_backtest  # noqa: E402
from efc.config import COMMODITIES, PROJECT_ROOT  # noqa: E402
from efc.data.eia import load_prices  # noqa: E402
from efc.metrics import drawdown, performance_summary, sharpe_by_period  # noqa: E402
from efc.portfolio import (  # noqa: E402
    build_panel,
    ewma_vol,
    month_end_dates,
    scale_positions,
    strategy_directions,
)

REPORTS = PROJECT_ROOT / "reports"
START = "1995-01-01"  # first year with >= 3 commodities and a full signal history

PERIODS = {
    "1995-2003": ("1995", "2003"),
    "2004-2008 supercycle": ("2004", "2008-06"),
    "2008 H2 crash": ("2008-07", "2008-12"),
    "2009-2014 H1": ("2009", "2014-06"),
    "2014-2016 oil glut": ("2014-07", "2016"),
    "2017-2019": ("2017", "2019"),
    "2020 Covid": ("2020", "2020"),
    "2021-2024 energy crisis": ("2021", "2024"),
}

# Categorical slots (validated for CVD separation); neutral grey for the benchmark.
COLORS = {
    "Long only": "#8a8a85",
    "TS carry": "#2a78d6",
    "XS carry": "#eb6834",
    "TS carry SA": "#1baf7a",
    "XS carry SA": "#eda100",
}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e6e5e0"


def _style(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED, length=0)


def _fmt(x: float, col: str) -> str:
    if pd.isna(x):
        return "n/a"
    if col in {"Sharpe", "Sortino", "Calmar", "Skew", "Turnover / yr"}:
        return f"{x:.2f}"
    return f"{x:.1%}"


def to_markdown(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| Strategy | " + " | ".join(cols) + " |", "|---" + "|---:" * len(cols) + "|"]
    for name, row in df.iterrows():
        lines.append(f"| {name} | " + " | ".join(_fmt(row[c], c) for c in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cost-bps", type=float, default=5.0)
    parser.add_argument("--target-vol", type=float, default=0.10)
    parser.add_argument("--roll-days", type=int, default=5)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()

    kw = {"data_dir": args.data_dir} if args.data_dir else {}
    prices = {k: load_prices(k, **kw) for k in COMMODITIES}
    panel = build_panel(prices, roll_days=args.roll_days)
    vol = ewma_vol(panel.returns)
    rebalance = month_end_dates(panel.returns.index)

    results, summary, by_period = {}, {}, {}
    for name, direction in strategy_directions(panel).items():
        w = scale_positions(direction, vol, rebalance, target_vol=args.target_vol)
        res = run_backtest(panel.returns, w, panel.rolls, cost_bps=args.cost_bps)
        net = res.net.loc[START:]
        results[name] = net
        summary[name] = performance_summary(net, res.turnover.loc[START:])
        summary[name]["Cost drag / yr"] = res.costs.loc[START:].mean() * 252
        by_period[name] = sharpe_by_period(net, PERIODS)

    table = pd.DataFrame(summary).T
    periods = pd.DataFrame(by_period).T
    print(table.round(3).to_string())
    print()
    print(periods.round(2).to_string())

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "figures").mkdir(exist_ok=True)
    end = panel.returns.index[-1]
    md = [
        "# Results",
        "",
        f"Net of costs ({args.cost_bps:g} bps per side), {START[:4]}-{end:%Y-%m}, "
        f"monthly rebalancing, {args.target_vol:.0%} ex-ante vol per asset, "
        f"roll {args.roll_days} trading days before expiry.",
        "",
        "## Performance",
        "",
        to_markdown(table),
        "",
        "## Sharpe ratio by sub-period",
        "",
        "| Strategy | " + " | ".join(periods.columns) + " |",
        "|---" + "|---:" * len(periods.columns) + "|",
    ]
    for name, row in periods.iterrows():
        md.append(f"| {name} | " + " | ".join(f"{v:.2f}" for v in row) + " |")
    (REPORTS / "results.md").write_text("\n".join(md) + "\n")

    # Figure 1: cumulative net returns, log scale
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150)
    ends = {}
    for name in COLORS:
        wealth = (1 + results[name].fillna(0)).cumprod()
        ls = (0, (4, 2)) if name == "Long only" else "-"
        ax.plot(wealth.index, wealth, color=COLORS[name], lw=1.6, ls=ls, label=name)
        ends[name] = np.log10(wealth.iloc[-1])
    # direct labels at the line ends, nudged apart so they never overlap
    placed: list[tuple[str, float]] = []
    for name, y in sorted(ends.items(), key=lambda kv: kv[1]):
        if placed and y - placed[-1][1] < 0.022:
            y = placed[-1][1] + 0.022
        placed.append((name, y))
    last = results["Long only"].index[-1]
    for name, y in placed:
        ax.annotate(
            name, (last, 10**y), xytext=(6, 0), textcoords="offset points",
            va="center", fontsize=8, color=INK,
        )
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.8, 1, 1.25, 1.5, 2, 3]))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_ylabel("Growth of $1 (log scale)", color=MUTED)
    ax.set_title(
        "Energy futures strategies, net of costs", loc="left", color=INK, fontsize=12
    )
    ax.legend(frameon=False, ncol=5, loc="upper left", fontsize=8, labelcolor=INK)
    _style(ax)
    ax.set_xlim(right=ax.get_xlim()[1] + 900)
    fig.tight_layout()
    fig.savefig(REPORTS / "figures" / "cumulative.png")
    plt.close(fig)

    # Figure 2: drawdowns, combined strategy vs long only
    fig, ax = plt.subplots(figsize=(10, 3.6), dpi=150)
    for name in ("Long only", "TS carry SA"):
        dd = drawdown(results[name])
        ls = (0, (4, 2)) if name == "Long only" else "-"
        ax.plot(dd.index, dd, color=COLORS[name], lw=1.4, ls=ls, label=name)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Drawdowns", loc="left", color=INK, fontsize=12)
    ax.legend(frameon=False, loc="lower left", fontsize=8, labelcolor=INK)
    _style(ax)
    fig.tight_layout()
    fig.savefig(REPORTS / "figures" / "drawdowns.png")
    plt.close(fig)
    print(f"\nWrote {REPORTS / 'results.md'} and figures.")


if __name__ == "__main__":
    main()
