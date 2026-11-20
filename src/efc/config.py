"""Commodity universe and data-source configuration.

EIA publishes daily NYMEX settlement prices for the first four listed contracts
("contract 1" = nearest to expiry) of several energy futures. We reference them
through their APIv1 series IDs, which the APIv2 ``/v2/seriesid/{id}`` route still
accepts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ExpiryRule = Literal["wti", "henry_hub", "last_bday_prior_month"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

N_CONTRACTS = 4


@dataclass(frozen=True)
class Commodity:
    key: str
    name: str
    unit: str
    eia_series: tuple[str, ...]  # one EIA series id per contract rank 1..N
    expiry_rule: ExpiryRule


def _series(template: str) -> tuple[str, ...]:
    return tuple(template.format(i=i) for i in range(1, N_CONTRACTS + 1))


COMMODITIES: dict[str, Commodity] = {
    "wti": Commodity(
        key="wti",
        name="WTI Crude Oil (NYMEX CL)",
        unit="USD/bbl",
        eia_series=_series("PET.RCLC{i}.D"),
        expiry_rule="wti",
    ),
    "natgas": Commodity(
        key="natgas",
        name="Henry Hub Natural Gas (NYMEX NG)",
        unit="USD/MMBtu",
        eia_series=_series("NG.RNGC{i}.D"),
        expiry_rule="henry_hub",
    ),
    "rbob": Commodity(
        key="rbob",
        name="RBOB Gasoline (NYMEX RB)",
        unit="USD/gal",
        eia_series=_series("PET.EER_EPMRR_PE{i}_Y35NY_DPG.D"),
        expiry_rule="last_bday_prior_month",
    ),
    "heating_oil": Commodity(
        key="heating_oil",
        name="NY Harbor ULSD / Heating Oil (NYMEX HO)",
        unit="USD/gal",
        eia_series=_series("PET.EER_EPD2F_PE{i}_Y35NY_DPG.D"),
        expiry_rule="last_bday_prior_month",
    ),
}
