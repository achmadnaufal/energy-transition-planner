"""
Renewable Energy Capacity Optimizer for coal-to-renewables transition planning.

Helps coal mining companies and energy utilities plan the transition from
coal-fired capacity to renewable energy generation through:
  - Renewable energy mix optimization (solar, wind, hydro, geothermal)
  - Coal capacity retirement scheduling
  - Capital expenditure (CapEx) estimation
  - LCOE (Levelized Cost of Energy) comparison
  - Grid stability and capacity factor analysis
  - Transition timeline milestones

Reference sources:
  - IRENA Renewable Power Generation Costs (2023)
  - IEA Coal in Net Zero Transitions (2021)
  - BNEF New Energy Outlook 2023
  - PLN RUPTL 2023-2032 (for Indonesia-specific context)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RenewableType(str, Enum):
    """Types of renewable energy technologies considered."""
    SOLAR_PV = "solar_pv"
    WIND_ONSHORE = "wind_onshore"
    WIND_OFFSHORE = "wind_offshore"
    HYDRO = "hydro"
    GEOTHERMAL = "geothermal"
    BIOMASS = "biomass"


# Technology parameters (2024 data, tropical/SE Asia context where applicable)
# Source: IRENA 2023, BNEF 2023
TECH_PARAMS: Dict[RenewableType, Dict] = {
    RenewableType.SOLAR_PV: {
        "capex_usd_per_kw": 650,
        "opex_usd_per_kw_year": 12,
        "capacity_factor": 0.18,   # Tropical average
        "lifetime_years": 25,
        "lcoe_usd_per_mwh": 45,
        "construction_years": 1,
        "grid_stability_index": 0.6,  # Lower = less dispatchable
    },
    RenewableType.WIND_ONSHORE: {
        "capex_usd_per_kw": 1100,
        "opex_usd_per_kw_year": 25,
        "capacity_factor": 0.28,
        "lifetime_years": 25,
        "lcoe_usd_per_mwh": 55,
        "construction_years": 2,
        "grid_stability_index": 0.65,
    },
    RenewableType.WIND_OFFSHORE: {
        "capex_usd_per_kw": 2800,
        "opex_usd_per_kw_year": 80,
        "capacity_factor": 0.38,
        "lifetime_years": 25,
        "lcoe_usd_per_mwh": 95,
        "construction_years": 3,
        "grid_stability_index": 0.70,
    },
    RenewableType.HYDRO: {
        "capex_usd_per_kw": 1800,
        "opex_usd_per_kw_year": 20,
        "capacity_factor": 0.42,
        "lifetime_years": 40,
        "lcoe_usd_per_mwh": 40,
        "construction_years": 4,
        "grid_stability_index": 0.90,  # Dispatchable
    },
    RenewableType.GEOTHERMAL: {
        "capex_usd_per_kw": 3200,
        "opex_usd_per_kw_year": 95,
        "capacity_factor": 0.85,
        "lifetime_years": 30,
        "lcoe_usd_per_mwh": 58,
        "construction_years": 5,
        "grid_stability_index": 0.95,  # Baseload
    },
    RenewableType.BIOMASS: {
        "capex_usd_per_kw": 2200,
        "opex_usd_per_kw_year": 90,
        "capacity_factor": 0.70,
        "lifetime_years": 25,
        "lcoe_usd_per_mwh": 85,
        "construction_years": 2,
        "grid_stability_index": 0.85,
    },
}


@dataclass
class CoalAsset:
    """A coal-fired power plant or mine-mouth generation asset."""
    asset_id: str
    name: str
    coal_capacity_mw: float         # Current coal generation capacity (MW)
    annual_generation_gwh: float    # Annual coal electricity generation
    retirement_year: int            # Planned or forced retirement year
    coal_lcoe_usd_per_mwh: float    # Current LCOE of coal

    def __post_init__(self):
        if self.coal_capacity_mw <= 0:
            raise ValueError(f"coal_capacity_mw must be positive ({self.asset_id})")
        if self.annual_generation_gwh < 0:
            raise ValueError(f"annual_generation_gwh must be non-negative ({self.asset_id})")
        if self.coal_lcoe_usd_per_mwh <= 0:
            raise ValueError(f"coal_lcoe_usd_per_mwh must be positive ({self.asset_id})")


@dataclass
class RenewableMixComponent:
    """A single renewable technology allocation in a capacity plan."""
    tech_type: RenewableType
    capacity_mw: float
    allocation_pct: float     # Share of total renewable capacity (%)

    @property
    def annual_generation_gwh(self) -> float:
        cf = TECH_PARAMS[self.tech_type]["capacity_factor"]
        return self.capacity_mw * cf * 8760 / 1000  # MW × CF × hours_per_year / 1000

    @property
    def total_capex_usd(self) -> float:
        capex_kw = TECH_PARAMS[self.tech_type]["capex_usd_per_kw"]
        return self.capacity_mw * 1000 * capex_kw  # MW × 1000 kW/MW × USD/kW

    @property
    def lcoe_usd_per_mwh(self) -> float:
        return TECH_PARAMS[self.tech_type]["lcoe_usd_per_mwh"]


@dataclass
class TransitionPlan:
    """Complete renewable energy transition plan for a coal asset."""
    asset_id: str
    coal_asset_name: str
    coal_capacity_mw: float
    renewable_mix: List[RenewableMixComponent]
    total_renewable_capacity_mw: float
    total_capex_usd: float
    capacity_adequacy_ratio: float     # Renewable gen / coal gen (should be ≥ 1.0)
    weighted_avg_lcoe_usd_per_mwh: float
    weighted_grid_stability_index: float
    lcoe_delta_vs_coal: float          # Positive = renewables more expensive
    earliest_completion_year: int
    milestones: List[Dict]
    warnings: List[str]

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "coal_asset_name": self.coal_asset_name,
            "coal_capacity_mw": self.coal_capacity_mw,
            "total_renewable_mw": round(self.total_renewable_capacity_mw, 1),
            "total_capex_usd": round(self.total_capex_usd, 0),
            "capacity_adequacy_ratio": round(self.capacity_adequacy_ratio, 3),
            "weighted_lcoe_usd_per_mwh": round(self.weighted_avg_lcoe_usd_per_mwh, 2),
            "grid_stability_index": round(self.weighted_grid_stability_index, 3),
            "lcoe_delta_vs_coal": round(self.lcoe_delta_vs_coal, 2),
            "earliest_completion_year": self.earliest_completion_year,
            "milestones": self.milestones,
            "warnings": self.warnings,
            "mix_breakdown": [
                {
                    "technology": c.tech_type.value,
                    "capacity_mw": round(c.capacity_mw, 1),
                    "allocation_pct": round(c.allocation_pct, 1),
                    "annual_gwh": round(c.annual_generation_gwh, 1),
                    "capex_usd": round(c.total_capex_usd, 0),
                    "lcoe_usd_per_mwh": c.lcoe_usd_per_mwh,
                }
                for c in self.renewable_mix
            ],
        }


class RenewableCapacityOptimizer:
    """
    Plan and optimize renewable energy capacity to replace coal generation.

    Given a coal asset and a desired technology mix (as percentage allocations),
    the optimizer calculates the required renewable capacity, CapEx, LCOE,
    grid stability score, and a phased transition timeline.

    Parameters
    ----------
    capacity_buffer_pct : float
        Extra renewable capacity above coal baseline (default 20% overcapacity
        to account for variable renewable capacity factors).
    base_year : int
        Current year for milestone planning (default 2025).

    Examples
    --------
    >>> optimizer = RenewableCapacityOptimizer()
    >>> coal = CoalAsset("PLT-001", "Suralaya Unit 1", 400, 2800, 2030, 65.0)
    >>> mix = {RenewableType.SOLAR_PV: 50.0, RenewableType.GEOTHERMAL: 30.0, RenewableType.HYDRO: 20.0}
    >>> plan = optimizer.optimize(coal, mix)
    >>> print(f"CapEx: USD {plan.total_capex_usd:,.0f}")
    """

    def __init__(
        self,
        capacity_buffer_pct: float = 20.0,
        base_year: int = 2025,
    ) -> None:
        if not 0 <= capacity_buffer_pct <= 100:
            raise ValueError("capacity_buffer_pct must be 0–100")
        self.capacity_buffer_pct = capacity_buffer_pct
        self.base_year = base_year

    def _validate_mix(self, mix: Dict[RenewableType, float]) -> None:
        if not mix:
            raise ValueError("Technology mix cannot be empty.")
        total = sum(mix.values())
        if abs(total - 100.0) > 0.5:
            raise ValueError(f"Mix allocations must sum to 100%, got {total:.1f}%")
        for tech, pct in mix.items():
            if pct < 0:
                raise ValueError(f"Allocation for {tech.value} cannot be negative.")

    def _build_milestones(
        self, mix: Dict[RenewableType, float], base_year: int, retirement_year: int
    ) -> Tuple[List[Dict], int]:
        """Generate phased milestone plan based on construction times."""
        milestones = []
        latest_completion = base_year

        for tech, pct in mix.items():
            if pct <= 0:
                continue
            construction = TECH_PARAMS[tech]["construction_years"]
            start_year = base_year
            completion_year = start_year + construction
            latest_completion = max(latest_completion, completion_year)
            milestones.append({
                "technology": tech.value,
                "allocation_pct": pct,
                "start_year": start_year,
                "completion_year": completion_year,
            })

        return sorted(milestones, key=lambda m: m["completion_year"]), latest_completion

    def optimize(
        self,
        coal_asset: CoalAsset,
        mix: Dict[RenewableType, float],
    ) -> TransitionPlan:
        """
        Generate a renewable capacity transition plan for a coal asset.

        Parameters
        ----------
        coal_asset : CoalAsset
        mix : dict {RenewableType: allocation_pct}
            Desired technology mix. Allocations must sum to 100%.

        Returns
        -------
        TransitionPlan
        """
        self._validate_mix(mix)

        warnings: List[str] = []

        # Target capacity with buffer
        target_capacity = coal_asset.coal_capacity_mw * (1 + self.capacity_buffer_pct / 100)

        components = []
        total_capex = 0.0
        total_gen_gwh = 0.0
        weighted_lcoe_sum = 0.0
        weighted_stability_sum = 0.0
        total_mw = 0.0

        for tech, pct in mix.items():
            if pct <= 0:
                continue
            cap_mw = target_capacity * pct / 100
            comp = RenewableMixComponent(tech_type=tech, capacity_mw=cap_mw, allocation_pct=pct)
            components.append(comp)
            total_capex += comp.total_capex_usd
            total_gen_gwh += comp.annual_generation_gwh
            weighted_lcoe_sum += comp.lcoe_usd_per_mwh * pct
            weighted_stability_sum += TECH_PARAMS[tech]["grid_stability_index"] * pct
            total_mw += cap_mw

        weighted_lcoe = weighted_lcoe_sum / 100
        weighted_stability = weighted_stability_sum / 100

        capacity_adequacy = total_gen_gwh / coal_asset.annual_generation_gwh if coal_asset.annual_generation_gwh > 0 else 0.0

        if capacity_adequacy < 1.0:
            warnings.append(
                f"CAPACITY SHORTFALL: Renewable mix generates {capacity_adequacy:.2f}× of coal baseline. "
                "Consider increasing capacity buffer or adding dispatchable technologies."
            )

        if weighted_stability < 0.70:
            warnings.append(
                f"LOW GRID STABILITY: Weighted stability index {weighted_stability:.2f}. "
                "Add geothermal, hydro, or biomass for firm capacity."
            )

        if weighted_lcoe > coal_asset.coal_lcoe_usd_per_mwh * 1.5:
            warnings.append(
                f"HIGH COST: Renewable LCOE (${weighted_lcoe:.0f}/MWh) is >50% above "
                f"coal LCOE (${coal_asset.coal_lcoe_usd_per_mwh:.0f}/MWh)."
            )

        milestones, earliest_completion = self._build_milestones(
            mix, self.base_year, coal_asset.retirement_year
        )

        if earliest_completion > coal_asset.retirement_year:
            warnings.append(
                f"TIMELINE RISK: Earliest completion {earliest_completion} exceeds "
                f"coal retirement year {coal_asset.retirement_year}. "
                "Fast-track permitting or earlier project start required."
            )

        return TransitionPlan(
            asset_id=coal_asset.asset_id,
            coal_asset_name=coal_asset.name,
            coal_capacity_mw=coal_asset.coal_capacity_mw,
            renewable_mix=components,
            total_renewable_capacity_mw=total_mw,
            total_capex_usd=total_capex,
            capacity_adequacy_ratio=capacity_adequacy,
            weighted_avg_lcoe_usd_per_mwh=weighted_lcoe,
            weighted_grid_stability_index=weighted_stability,
            lcoe_delta_vs_coal=weighted_lcoe - coal_asset.coal_lcoe_usd_per_mwh,
            earliest_completion_year=earliest_completion,
            milestones=milestones,
            warnings=warnings,
        )

    def compare_mixes(
        self,
        coal_asset: CoalAsset,
        candidate_mixes: List[Dict[RenewableType, float]],
    ) -> List[TransitionPlan]:
        """
        Compare multiple technology mix candidates for the same coal asset.
        Returns plans sorted by weighted LCOE (cheapest first).
        """
        plans = [self.optimize(coal_asset, m) for m in candidate_mixes]
        return sorted(plans, key=lambda p: p.weighted_avg_lcoe_usd_per_mwh)
