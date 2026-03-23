"""
Stranded Asset Risk Calculator for Coal Mining Operations.

A stranded asset is an asset that suffers from unexpected write-downs,
underperformance, or premature decommissioning due to changes in regulation,
market dynamics, or technological disruption.

For coal mining companies, stranded asset risk arises from:
- Carbon pricing / emissions regulations
- Renewable energy price competition
- IEA Net Zero pathways and coal phase-out timelines
- Declining investor appetite (ESG divestment pressure)
- Declining thermal coal demand from power utilities

This module calculates stranded asset exposure and the value at risk
under multiple transition scenarios, using a discounted cash flow (DCF)
framework with scenario-weighted carbon costs.

References:
    - IEA World Energy Outlook 2023 (STEPS, APS, NZE scenarios)
    - Carbon Tracker Initiative: Unburnable Carbon
    - TCFD Guidance on Climate Scenarios

Author: github.com/achmadnaufal
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Carbon price trajectories (USD/tCO2e) — IEA 2023 WEO-based
# ---------------------------------------------------------------------------

CARBON_PRICE_PATHS: Dict[str, Dict[int, float]] = {
    # Stated Policies Scenario (STEPS) — low ambition
    "STEPS": {2026: 15, 2030: 25, 2035: 35, 2040: 45, 2050: 55},
    # Announced Pledges Scenario (APS) — moderate
    "APS":   {2026: 30, 2030: 60, 2035: 90, 2040: 120, 2050: 160},
    # Net Zero Emissions by 2050 (NZE) — high ambition
    "NZE":   {2026: 50, 2030: 130, 2035: 200, 2040: 250, 2050: 250},
}

# Scenario probability weights for expected value calculation
SCENARIO_WEIGHTS: Dict[str, float] = {
    "STEPS": 0.25,
    "APS":   0.45,
    "NZE":   0.30,
}


@dataclass
class CoalAsset:
    """
    Represents a coal mining asset subject to transition risk assessment.

    Attributes:
        asset_id: Unique identifier for the asset.
        asset_name: Human-readable name (mine name or field name).
        reserve_mt: Remaining coal reserve in million tonnes (Mt).
        annual_production_mt: Annual production capacity in Mt.
        mine_life_years: Remaining economic mine life in years.
        book_value_usd_m: Current book value in USD millions.
        annual_revenue_usd_m: Annual revenue in USD millions.
        annual_opex_usd_m: Annual operating expenditure in USD millions.
        scope1_intensity_tCO2e_per_t: Scope 1 GHG intensity (tCO2e per tonne produced).
        coal_grade: Coal grade for context (e.g., ``sub_bituminous``, ``thermal``).
        country: Country where asset is located.
    """

    asset_id: str
    asset_name: str
    reserve_mt: float
    annual_production_mt: float
    mine_life_years: int
    book_value_usd_m: float
    annual_revenue_usd_m: float
    annual_opex_usd_m: float
    scope1_intensity_tCO2e_per_t: float = 0.035  # tCO2e/t — typical Indonesian surface mine
    coal_grade: str = "sub_bituminous"
    country: str = "Indonesia"

    def __post_init__(self) -> None:
        if self.reserve_mt <= 0:
            raise ValueError("reserve_mt must be positive.")
        if self.annual_production_mt <= 0:
            raise ValueError("annual_production_mt must be positive.")
        if self.mine_life_years <= 0:
            raise ValueError("mine_life_years must be positive.")
        if self.book_value_usd_m < 0:
            raise ValueError("book_value_usd_m cannot be negative.")
        if self.scope1_intensity_tCO2e_per_t < 0:
            raise ValueError("scope1_intensity_tCO2e_per_t cannot be negative.")

    @property
    def annual_ebitda_usd_m(self) -> float:
        """Annual EBITDA before carbon costs (USD millions)."""
        return round(self.annual_revenue_usd_m - self.annual_opex_usd_m, 2)

    @property
    def annual_emissions_tCO2e(self) -> float:
        """Annual Scope 1 emissions (tCO2e) at full production."""
        return round(self.annual_production_mt * 1_000_000 * self.scope1_intensity_tCO2e_per_t, 0)


class StrandedAssetCalculator:
    """
    Calculates stranded asset risk and value at risk for coal mining assets.

    Uses a DCF framework with scenario-weighted carbon costs to estimate
    the difference between the asset's current book value and its NPV
    under transition scenarios. A positive stranded value indicates risk
    of write-down under that scenario.

    Attributes:
        discount_rate (float): WACC / discount rate for DCF (default 10%).
        assets (list[CoalAsset]): Registered coal assets.

    Example::

        calc = StrandedAssetCalculator(discount_rate=0.10)
        calc.add_asset(CoalAsset(
            asset_id="MN-KAL-001",
            asset_name="Kalimantan South Mine",
            reserve_mt=250.0,
            annual_production_mt=8.0,
            mine_life_years=30,
            book_value_usd_m=420.0,
            annual_revenue_usd_m=160.0,
            annual_opex_usd_m=105.0,
        ))
        report = calc.stranded_value_report("NZE")
        print(f"Stranded value (NZE): USD {report['total_stranded_usd_m']:.0f}M")
    """

    def __init__(self, discount_rate: float = 0.10) -> None:
        """
        Initialize the calculator.

        Args:
            discount_rate: Discount rate (WACC) used in DCF. Must be in (0, 1).

        Raises:
            ValueError: If discount_rate is not in valid range.
        """
        if not (0 < discount_rate < 1):
            raise ValueError("discount_rate must be between 0 and 1 (exclusive).")
        self.discount_rate = discount_rate
        self.assets: List[CoalAsset] = []

    # ------------------------------------------------------------------
    # Asset management
    # ------------------------------------------------------------------

    def add_asset(self, asset: CoalAsset) -> None:
        """
        Register a coal asset for analysis.

        Args:
            asset: A :class:`CoalAsset` instance.

        Raises:
            ValueError: If an asset with the same ID already exists.
        """
        if any(a.asset_id == asset.asset_id for a in self.assets):
            raise ValueError(f"Asset '{asset.asset_id}' already registered.")
        self.assets.append(asset)

    def remove_asset(self, asset_id: str) -> bool:
        """Remove an asset by ID. Returns True if removed."""
        before = len(self.assets)
        self.assets = [a for a in self.assets if a.asset_id != asset_id]
        return len(self.assets) < before

    # ------------------------------------------------------------------
    # Carbon cost interpolation
    # ------------------------------------------------------------------

    def _carbon_price_for_year(self, scenario: str, year: int) -> float:
        """
        Interpolate carbon price for a given year and scenario.

        Args:
            scenario: One of ``STEPS``, ``APS``, ``NZE``.
            year: Target year.

        Returns:
            Interpolated carbon price (USD/tCO2e).
        """
        if scenario not in CARBON_PRICE_PATHS:
            raise ValueError(f"scenario '{scenario}' not found. Use: {list(CARBON_PRICE_PATHS)}")
        path = CARBON_PRICE_PATHS[scenario]
        milestones = sorted(path.keys())

        if year <= milestones[0]:
            return path[milestones[0]]
        if year >= milestones[-1]:
            return path[milestones[-1]]

        # Linear interpolation
        for i in range(len(milestones) - 1):
            y0, y1 = milestones[i], milestones[i + 1]
            if y0 <= year <= y1:
                p0, p1 = path[y0], path[y1]
                return p0 + (p1 - p0) * (year - y0) / (y1 - y0)
        return path[milestones[-1]]

    # ------------------------------------------------------------------
    # DCF valuation
    # ------------------------------------------------------------------

    def asset_npv(self, asset: CoalAsset, scenario: str, base_year: int = 2026) -> float:
        """
        Calculate NPV of a coal asset under a carbon price scenario.

        Annual cash flow = Revenue − OpEx − Carbon cost
        Carbon cost = annual emissions × carbon price

        Args:
            asset: :class:`CoalAsset` to evaluate.
            scenario: Carbon price scenario (``STEPS`` / ``APS`` / ``NZE``).
            base_year: Year from which DCF is calculated.

        Returns:
            Asset NPV in USD millions.
        """
        npv = 0.0
        for t in range(1, asset.mine_life_years + 1):
            year = base_year + t
            carbon_price = self._carbon_price_for_year(scenario, year)
            annual_carbon_cost_m = (
                asset.annual_emissions_tCO2e * carbon_price / 1_000_000
            )
            annual_cf = asset.annual_ebitda_usd_m - annual_carbon_cost_m
            discount_factor = (1 + self.discount_rate) ** t
            npv += annual_cf / discount_factor
        return round(npv, 2)

    def stranded_value(self, asset: CoalAsset, scenario: str) -> Dict:
        """
        Calculate stranded value exposure for a single asset.

        Stranded Value = Book Value − NPV (under scenario)
        Positive stranded value → risk of write-down.

        Args:
            asset: Asset to evaluate.
            scenario: Transition scenario.

        Returns:
            dict with NPV, stranded_value_usd_m, and stranded_pct_of_book.
        """
        npv = self.asset_npv(asset, scenario)
        stranded = round(asset.book_value_usd_m - npv, 2)
        stranded_pct = (
            round(stranded / asset.book_value_usd_m * 100, 1)
            if asset.book_value_usd_m > 0 else 0.0
        )
        return {
            "asset_id": asset.asset_id,
            "asset_name": asset.asset_name,
            "book_value_usd_m": asset.book_value_usd_m,
            "npv_usd_m": npv,
            "stranded_value_usd_m": stranded,
            "stranded_pct_of_book": stranded_pct,
            "scenario": scenario,
            "at_risk": stranded > 0,
        }

    # ------------------------------------------------------------------
    # Portfolio-level reporting
    # ------------------------------------------------------------------

    def stranded_value_report(self, scenario: str) -> Dict:
        """
        Generate a portfolio-level stranded asset report for a scenario.

        Args:
            scenario: Transition scenario (``STEPS`` / ``APS`` / ``NZE``).

        Returns:
            dict with:

            - ``scenario`` – scenario name
            - ``total_book_value_usd_m`` – portfolio book value
            - ``total_npv_usd_m`` – aggregate NPV under scenario
            - ``total_stranded_usd_m`` – aggregate stranded exposure
            - ``stranded_pct_of_portfolio`` – as % of total book value
            - ``assets_at_risk`` – count with positive stranded value
            - ``by_asset`` – per-asset stranded value breakdown
        """
        if not self.assets:
            return {"scenario": scenario, "total_stranded_usd_m": 0.0, "assets_at_risk": 0}

        by_asset = [self.stranded_value(a, scenario) for a in self.assets]
        total_book = round(sum(a.book_value_usd_m for a in self.assets), 2)
        total_npv = round(sum(r["npv_usd_m"] for r in by_asset), 2)
        total_stranded = round(total_book - total_npv, 2)
        stranded_pct = round(total_stranded / total_book * 100, 1) if total_book > 0 else 0.0
        at_risk = sum(1 for r in by_asset if r["at_risk"])

        return {
            "scenario": scenario,
            "n_assets": len(self.assets),
            "total_book_value_usd_m": total_book,
            "total_npv_usd_m": total_npv,
            "total_stranded_usd_m": total_stranded,
            "stranded_pct_of_portfolio": stranded_pct,
            "assets_at_risk": at_risk,
            "by_asset": by_asset,
        }

    def expected_stranded_value(self, base_year: int = 2026) -> Dict:
        """
        Probability-weighted expected stranded asset value across all scenarios.

        Weights: STEPS=25%, APS=45%, NZE=30% (see :data:`SCENARIO_WEIGHTS`).

        Returns:
            dict with expected_stranded_usd_m and per-scenario breakdown.
        """
        by_scenario = {}
        expected = 0.0
        for scenario, weight in SCENARIO_WEIGHTS.items():
            report = self.stranded_value_report(scenario)
            stranded = report["total_stranded_usd_m"]
            by_scenario[scenario] = {
                "stranded_usd_m": stranded,
                "weight": weight,
                "weighted_usd_m": round(stranded * weight, 2),
            }
            expected += stranded * weight

        return {
            "expected_stranded_usd_m": round(expected, 2),
            "by_scenario": by_scenario,
            "scenario_weights": SCENARIO_WEIGHTS,
        }

    def __len__(self) -> int:
        return len(self.assets)

    def __repr__(self) -> str:
        return (
            f"StrandedAssetCalculator(discount_rate={self.discount_rate}, "
            f"assets={len(self.assets)})"
        )
