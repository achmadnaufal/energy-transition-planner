"""
Just Transition Impact Assessor for coal-dependent communities and regions.

A "just transition" ensures that the move away from fossil fuels supports
affected workers, communities, and regions, avoiding concentrated socioeconomic
harm. This module quantifies the workforce, economic, and social dimensions
of transition scenarios for coal mining operations.

Assessment dimensions (aligned with ILO Just Transition Guidelines 2015
and World Bank Just Transitions for All 2022):
  1. **Workforce displacement**: Direct and indirect jobs at risk by year
  2. **Economic diversification**: GDP dependence on coal revenues
  3. **Community vulnerability**: Infrastructure, healthcare, and education exposure
  4. **Transition support adequacy**: Reskilling capacity and severance coverage
  5. **Social protection gap**: Estimated funding gap for transition packages

References:
  - ILO Guidelines for a Just Transition (2015)
  - World Bank Just Transitions for All (2022)
  - OECD Fossil Fuel Employment Transition Strategies (2023)
  - Coal Authority UK — Transition Impact Framework

Author: github.com/achmadnaufal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class TransitionSpeed(str, Enum):
    """Coal phase-down speed scenarios aligned with IEA pathways."""
    GRADUAL = "gradual"        # ~15-20 year phase-down (STEPS-like)
    MODERATE = "moderate"      # ~10-12 year phase-down (APS-like)
    ACCELERATED = "accelerated"  # ~5-7 year phase-down (NZE-aligned)


class VulnerabilityLevel(str, Enum):
    """Overall community vulnerability to transition shock."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Indirect job multipliers by sector (jobs per direct mining job)
# Source: ILO, Oxford Economics, World Bank regional analysis
INDIRECT_JOB_MULTIPLIERS: Dict[str, float] = {
    "coal_mining": 2.8,       # Indonesian coal belt average
    "coal_transport": 1.5,
    "coal_processing": 1.2,
    "coal_power": 1.8,
}

# Cost per worker for transition support package (USD)
# Includes severance, reskilling, relocation subsidy (World Bank benchmarks)
TRANSITION_COST_PER_WORKER_USD: Dict[TransitionSpeed, float] = {
    TransitionSpeed.ACCELERATED: 18_000,  # Compressed timeline, higher per-worker cost
    TransitionSpeed.MODERATE: 12_000,
    TransitionSpeed.GRADUAL: 7_500,
}

# Phase-down timeline (years to full mine closure) by scenario
PHASE_DOWN_YEARS: Dict[TransitionSpeed, int] = {
    TransitionSpeed.GRADUAL: 18,
    TransitionSpeed.MODERATE: 10,
    TransitionSpeed.ACCELERATED: 6,
}


@dataclass
class MiningCommunity:
    """Socioeconomic profile of a community dependent on coal mining.

    Attributes:
        community_id: Unique identifier.
        community_name: Name of the district/township.
        country: Country code (e.g., 'ID', 'AU', 'ZA').
        total_population: Total resident population.
        direct_mining_jobs: Count of workers directly employed in mining.
        median_annual_income_usd: Median annual household income (USD).
        coal_gdp_share_pct: Coal's share of local/regional GDP (%).
        alternative_employers: Count of significant non-coal employers in region.
        reskilling_capacity_pct: % of displaced workers for whom reskilling
            programmes currently exist or are planned.
        social_safety_net_monthly_usd: Monthly social protection payment available
            to displaced workers (USD/worker).
        healthcare_index: Healthcare access index 0–100 (100 = full access).
        education_index: Education quality index 0–100 (100 = excellent).
        existing_commitments_usd_m: Existing government/company commitments
            for transition funding (USD millions).
    """

    community_id: str
    community_name: str
    country: str
    total_population: int
    direct_mining_jobs: int
    median_annual_income_usd: float
    coal_gdp_share_pct: float
    alternative_employers: int
    reskilling_capacity_pct: float = 30.0
    social_safety_net_monthly_usd: float = 0.0
    healthcare_index: float = 60.0
    education_index: float = 60.0
    existing_commitments_usd_m: float = 0.0

    def __post_init__(self) -> None:
        if self.total_population <= 0:
            raise ValueError("total_population must be positive")
        if self.direct_mining_jobs < 0:
            raise ValueError("direct_mining_jobs cannot be negative")
        if not (0 <= self.coal_gdp_share_pct <= 100):
            raise ValueError("coal_gdp_share_pct must be between 0 and 100")
        if not (0 <= self.reskilling_capacity_pct <= 100):
            raise ValueError("reskilling_capacity_pct must be between 0 and 100")
        if not (0 <= self.healthcare_index <= 100):
            raise ValueError("healthcare_index must be 0–100")
        if not (0 <= self.education_index <= 100):
            raise ValueError("education_index must be 0–100")

    @property
    def mining_employment_share_pct(self) -> float:
        """Direct mining jobs as % of total working-age population (approx.)."""
        working_age_pop = self.total_population * 0.55
        if working_age_pop == 0:
            return 0.0
        return (self.direct_mining_jobs / working_age_pop) * 100

    @property
    def estimated_indirect_jobs(self) -> int:
        """Estimated indirect jobs supported by mining (supply chain, services)."""
        return int(self.direct_mining_jobs * INDIRECT_JOB_MULTIPLIERS["coal_mining"])

    @property
    def total_at_risk_jobs(self) -> int:
        """Total direct + indirect jobs at risk from mine closure."""
        return self.direct_mining_jobs + self.estimated_indirect_jobs


@dataclass
class TransitionImpact:
    """Quantified transition impact assessment for a community and scenario.

    Attributes:
        community_id: Reference community.
        scenario: Transition speed scenario applied.
        phase_down_years: Years to full mine closure under scenario.
        direct_jobs_displaced: Total direct jobs lost.
        indirect_jobs_displaced: Estimated indirect job losses.
        total_jobs_at_risk: Sum of direct + indirect.
        jobs_reskillable: Estimated workers with reskilling pathway.
        jobs_uncovered: Workers without reskilling or transfer option.
        total_transition_cost_usd_m: Full cost of transition support package (USD M).
        existing_funding_usd_m: Committed funding from all sources (USD M).
        funding_gap_usd_m: Unmet transition funding need (USD M).
        gdp_shock_pct: Estimated GDP contraction from coal phase-out.
        vulnerability: Community vulnerability tier.
        annual_jobs_displaced: Year-by-year direct job displacement schedule.
        key_risks: Narrative risk factors.
        recommendations: Actionable recommendations.
    """

    community_id: str
    scenario: TransitionSpeed
    phase_down_years: int
    direct_jobs_displaced: int
    indirect_jobs_displaced: int
    total_jobs_at_risk: int
    jobs_reskillable: int
    jobs_uncovered: int
    total_transition_cost_usd_m: float
    existing_funding_usd_m: float
    funding_gap_usd_m: float
    gdp_shock_pct: float
    vulnerability: VulnerabilityLevel
    annual_jobs_displaced: Dict[int, int]
    key_risks: List[str]
    recommendations: List[str]


class JustTransitionImpactAssessor:
    """Assesses socioeconomic transition impacts for coal-dependent communities.

    Uses ILO and World Bank just transition frameworks to quantify workforce
    displacement, funding gaps, and community vulnerability across multiple
    coal phase-down speed scenarios.

    Example:
        >>> assessor = JustTransitionImpactAssessor()
        >>> community = MiningCommunity(
        ...     community_id="BERAU_001",
        ...     community_name="Berau District",
        ...     country="ID",
        ...     total_population=200_000,
        ...     direct_mining_jobs=12_500,
        ...     median_annual_income_usd=8_500,
        ...     coal_gdp_share_pct=58,
        ...     alternative_employers=3,
        ...     reskilling_capacity_pct=25,
        ... )
        >>> impact = assessor.assess(community, TransitionSpeed.MODERATE)
        >>> print(impact.vulnerability)
        VulnerabilityLevel.HIGH
    """

    def __init__(
        self,
        gdp_multiplier_direct: float = 2.5,
        safety_net_coverage_months: int = 12,
    ) -> None:
        """Initialise the assessor.

        Args:
            gdp_multiplier_direct: GDP impact multiplier per unit of coal GDP lost.
            safety_net_coverage_months: Months of social safety net per displaced worker.
        """
        self.gdp_multiplier_direct = gdp_multiplier_direct
        self.safety_net_coverage_months = safety_net_coverage_months

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(
        self,
        community: MiningCommunity,
        scenario: TransitionSpeed,
    ) -> TransitionImpact:
        """Run full just transition impact assessment for a community and scenario.

        Args:
            community: MiningCommunity profile.
            scenario: Transition speed (GRADUAL / MODERATE / ACCELERATED).

        Returns:
            TransitionImpact with full quantified assessment.
        """
        if not isinstance(community, MiningCommunity):
            raise TypeError("community must be a MiningCommunity instance")

        phase_down_yrs = PHASE_DOWN_YEARS[scenario]
        direct_displaced = community.direct_mining_jobs
        indirect_displaced = community.estimated_indirect_jobs
        total_at_risk = community.total_at_risk_jobs

        # Reskilling and uncovered
        reskillable = int(direct_displaced * community.reskilling_capacity_pct / 100)
        uncovered = max(0, direct_displaced - reskillable)

        # Transition cost
        cost_per_worker = TRANSITION_COST_PER_WORKER_USD[scenario]
        total_cost_usd_m = (direct_displaced * cost_per_worker) / 1_000_000
        gap_usd_m = max(0.0, total_cost_usd_m - community.existing_commitments_usd_m)

        # GDP shock estimation
        gdp_shock = self._estimate_gdp_shock(community, scenario)

        # Year-by-year displacement schedule (linear)
        annual_schedule = self._build_displacement_schedule(direct_displaced, phase_down_yrs)

        # Vulnerability scoring
        vulnerability = self._score_vulnerability(community, scenario, gap_usd_m)

        # Qualitative risk flags
        risks = self._identify_key_risks(community, scenario, gap_usd_m, uncovered)
        recs = self._generate_recommendations(community, scenario, vulnerability, uncovered)

        return TransitionImpact(
            community_id=community.community_id,
            scenario=scenario,
            phase_down_years=phase_down_yrs,
            direct_jobs_displaced=direct_displaced,
            indirect_jobs_displaced=indirect_displaced,
            total_jobs_at_risk=total_at_risk,
            jobs_reskillable=reskillable,
            jobs_uncovered=uncovered,
            total_transition_cost_usd_m=round(total_cost_usd_m, 2),
            existing_funding_usd_m=community.existing_commitments_usd_m,
            funding_gap_usd_m=round(gap_usd_m, 2),
            gdp_shock_pct=round(gdp_shock, 1),
            vulnerability=vulnerability,
            annual_jobs_displaced=annual_schedule,
            key_risks=risks,
            recommendations=recs,
        )

    def compare_scenarios(
        self, community: MiningCommunity
    ) -> Dict[TransitionSpeed, TransitionImpact]:
        """Run all three transition speed scenarios for side-by-side comparison.

        Args:
            community: MiningCommunity profile.

        Returns:
            Dict mapping TransitionSpeed → TransitionImpact.
        """
        return {speed: self.assess(community, speed) for speed in TransitionSpeed}

    def portfolio_vulnerability_summary(
        self, communities: List[MiningCommunity], scenario: TransitionSpeed
    ) -> Dict:
        """Aggregate vulnerability metrics across a portfolio of communities.

        Args:
            communities: List of MiningCommunity profiles.
            scenario: Transition speed scenario to apply uniformly.

        Returns:
            Dict with aggregate counts and funding gap totals.

        Raises:
            ValueError: If communities list is empty.
        """
        if not communities:
            raise ValueError("communities list cannot be empty")

        impacts = [self.assess(c, scenario) for c in communities]
        by_level: Dict[str, List[str]] = {v.value: [] for v in VulnerabilityLevel}
        for c, imp in zip(communities, impacts):
            by_level[imp.vulnerability.value].append(c.community_name)

        return {
            "scenario": scenario.value,
            "total_communities": len(communities),
            "total_direct_jobs_at_risk": sum(i.direct_jobs_displaced for i in impacts),
            "total_indirect_jobs_at_risk": sum(i.indirect_jobs_displaced for i in impacts),
            "total_funding_gap_usd_m": round(sum(i.funding_gap_usd_m for i in impacts), 2),
            "total_uncovered_workers": sum(i.jobs_uncovered for i in impacts),
            "vulnerability_breakdown": by_level,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _estimate_gdp_shock(
        self, community: MiningCommunity, scenario: TransitionSpeed
    ) -> float:
        """Estimate GDP contraction from coal phase-out as % of regional GDP.

        Uses coal GDP share adjusted for speed (faster = larger shock per year).
        """
        speed_factor = {
            TransitionSpeed.GRADUAL: 0.8,
            TransitionSpeed.MODERATE: 1.0,
            TransitionSpeed.ACCELERATED: 1.35,
        }[scenario]
        return community.coal_gdp_share_pct * speed_factor * self.gdp_multiplier_direct / 100

    @staticmethod
    def _build_displacement_schedule(
        total_jobs: int, phase_years: int
    ) -> Dict[int, int]:
        """Build linear job displacement schedule year by year.

        Args:
            total_jobs: Total direct jobs to be displaced.
            phase_years: Number of years over which displacement occurs.

        Returns:
            Dict mapping year_offset (1-based) to jobs displaced that year.
        """
        jobs_per_year = total_jobs // phase_years
        remainder = total_jobs % phase_years
        schedule: Dict[int, int] = {}
        for yr in range(1, phase_years + 1):
            schedule[yr] = jobs_per_year + (1 if yr <= remainder else 0)
        return schedule

    def _score_vulnerability(
        self,
        community: MiningCommunity,
        scenario: TransitionSpeed,
        funding_gap_usd_m: float,
    ) -> VulnerabilityLevel:
        """Compute community vulnerability level using composite scoring.

        Scores four sub-dimensions on 0–25 scale and sums to 0–100.
        """
        # Economic dependence sub-score (0–25)
        econ_score = min(25, community.coal_gdp_share_pct * 0.4)

        # Workforce sub-score (0–25)
        workforce_score = min(25, community.mining_employment_share_pct * 1.5)

        # Social safety net sub-score (0–25): lower safety net = higher vulnerability
        safety_net_score = max(0, 25 - community.social_safety_net_monthly_usd / 40)

        # Reskilling gap sub-score (0–25): lower capacity = higher vulnerability
        reskill_score = max(0, 25 - community.reskilling_capacity_pct * 0.25)

        # Speed multiplier
        speed_mult = {
            TransitionSpeed.GRADUAL: 0.85,
            TransitionSpeed.MODERATE: 1.0,
            TransitionSpeed.ACCELERATED: 1.25,
        }[scenario]

        composite = (econ_score + workforce_score + safety_net_score + reskill_score) * speed_mult

        if composite < 30:
            return VulnerabilityLevel.LOW
        elif composite < 55:
            return VulnerabilityLevel.MEDIUM
        elif composite < 75:
            return VulnerabilityLevel.HIGH
        else:
            return VulnerabilityLevel.CRITICAL

    @staticmethod
    def _identify_key_risks(
        community: MiningCommunity,
        scenario: TransitionSpeed,
        funding_gap_usd_m: float,
        uncovered_workers: int,
    ) -> List[str]:
        """Identify qualitative risk factors."""
        risks: List[str] = []
        if community.coal_gdp_share_pct > 50:
            risks.append(
                f"Extreme economic concentration: coal represents {community.coal_gdp_share_pct:.0f}% of local GDP."
            )
        if community.alternative_employers < 5:
            risks.append(
                f"Limited economic diversification: only {community.alternative_employers} alternative employers in region."
            )
        if scenario == TransitionSpeed.ACCELERATED:
            risks.append("Accelerated timeline compresses reskilling window to <6 years.")
        if funding_gap_usd_m > 50:
            risks.append(f"Large funding gap: USD {funding_gap_usd_m:.1f}M unmet transition support.")
        if uncovered_workers > community.direct_mining_jobs * 0.5:
            risks.append(
                f"{uncovered_workers:,} workers ({uncovered_workers/community.direct_mining_jobs*100:.0f}%) "
                "have no identified reskilling or redeployment pathway."
            )
        if community.healthcare_index < 50:
            risks.append("Low healthcare index may compound transition-related mental health impacts.")
        if not risks:
            risks.append("No critical risk flags identified under this scenario.")
        return risks

    @staticmethod
    def _generate_recommendations(
        community: MiningCommunity,
        scenario: TransitionSpeed,
        vulnerability: VulnerabilityLevel,
        uncovered_workers: int,
    ) -> List[str]:
        """Generate actionable transition support recommendations."""
        recs: List[str] = []
        if vulnerability in (VulnerabilityLevel.HIGH, VulnerabilityLevel.CRITICAL):
            recs.append("Prioritise this community for government-backed transition support funding.")
        if community.reskilling_capacity_pct < 40:
            recs.append(
                "Expand vocational training partnerships with regional technical institutes "
                "(target: ≥60% reskilling capacity within 3 years)."
            )
        if community.alternative_employers < 5:
            recs.append(
                "Develop economic diversification strategy: attract renewable energy, "
                "agri-processing, or eco-tourism investment."
            )
        if community.social_safety_net_monthly_usd < 100:
            recs.append(
                "Establish or expand monthly social protection payments for displaced workers "
                "(minimum USD 150/month for 18-month bridge period)."
            )
        if scenario == TransitionSpeed.ACCELERATED:
            recs.append(
                "Accelerated scenario requires immediate activation of Just Transition Fund; "
                "recommend emergency planning engagement with ILO/World Bank."
            )
        if uncovered_workers > 500:
            recs.append(
                f"Target {uncovered_workers:,} uncovered workers with portable skills assessment "
                "and sector-agnostic digital literacy programmes."
            )
        if not recs:
            recs.append("Continue monitoring and maintain existing transition support programmes.")
        return recs
