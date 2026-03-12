"""Unit tests for JustTransitionImpactAssessor."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from just_transition_assessor import (
    JustTransitionImpactAssessor,
    MiningCommunity,
    TransitionSpeed,
    VulnerabilityLevel,
    PHASE_DOWN_YEARS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_community(
    community_id="BERAU_001",
    population=200_000,
    direct_jobs=12_500,
    coal_gdp_pct=58.0,
    alt_employers=3,
    reskilling_pct=25.0,
    safety_net=0.0,
    healthcare=60.0,
    education=55.0,
    commitments_usd_m=10.0,
) -> MiningCommunity:
    return MiningCommunity(
        community_id=community_id,
        community_name="Test District",
        country="ID",
        total_population=population,
        direct_mining_jobs=direct_jobs,
        median_annual_income_usd=8_500,
        coal_gdp_share_pct=coal_gdp_pct,
        alternative_employers=alt_employers,
        reskilling_capacity_pct=reskilling_pct,
        social_safety_net_monthly_usd=safety_net,
        healthcare_index=healthcare,
        education_index=education,
        existing_commitments_usd_m=commitments_usd_m,
    )


# ---------------------------------------------------------------------------
# MiningCommunity validation
# ---------------------------------------------------------------------------

class TestMiningCommunity:
    def test_mining_employment_share(self):
        c = make_community(population=100_000, direct_jobs=5_000)
        # 5000 / (100000 * 0.55) * 100 ≈ 9.09%
        assert abs(c.mining_employment_share_pct - 9.09) < 0.1

    def test_estimated_indirect_jobs(self):
        c = make_community(direct_jobs=1_000)
        # multiplier 2.8
        assert c.estimated_indirect_jobs == 2_800

    def test_total_at_risk_jobs(self):
        c = make_community(direct_jobs=1_000)
        assert c.total_at_risk_jobs == 3_800

    def test_zero_population_raises(self):
        with pytest.raises(ValueError):
            make_community(population=0)

    def test_negative_jobs_raises(self):
        with pytest.raises(ValueError):
            make_community(direct_jobs=-1)

    def test_invalid_gdp_share_raises(self):
        with pytest.raises(ValueError):
            make_community(coal_gdp_pct=110)


# ---------------------------------------------------------------------------
# JustTransitionImpactAssessor
# ---------------------------------------------------------------------------

class TestAssessor:
    def setup_method(self):
        self.assessor = JustTransitionImpactAssessor()

    def test_phase_down_years(self):
        c = make_community()
        for speed in TransitionSpeed:
            impact = self.assessor.assess(c, speed)
            assert impact.phase_down_years == PHASE_DOWN_YEARS[speed]

    def test_direct_jobs_equals_community_jobs(self):
        c = make_community(direct_jobs=5_000)
        impact = self.assessor.assess(c, TransitionSpeed.MODERATE)
        assert impact.direct_jobs_displaced == 5_000

    def test_funding_gap_positive_when_cost_exceeds_commitments(self):
        c = make_community(direct_jobs=10_000, commitments_usd_m=5.0)
        impact = self.assessor.assess(c, TransitionSpeed.ACCELERATED)
        # Cost = 10000 * 18000 / 1e6 = 180.0 USD M >> 5 USD M commitment
        assert impact.funding_gap_usd_m > 0

    def test_zero_funding_gap_when_fully_covered(self):
        c = make_community(direct_jobs=100, commitments_usd_m=10.0)
        impact = self.assessor.assess(c, TransitionSpeed.GRADUAL)
        # Cost = 100 * 7500 / 1e6 = 0.75M < 10M commitment
        assert impact.funding_gap_usd_m == 0.0

    def test_annual_schedule_sums_to_total_jobs(self):
        c = make_community(direct_jobs=100)
        for speed in TransitionSpeed:
            impact = self.assessor.assess(c, speed)
            assert sum(impact.annual_jobs_displaced.values()) == 100

    def test_accelerated_higher_vulnerability_than_gradual(self):
        c = make_community(coal_gdp_pct=65, reskilling_pct=20)
        accel = self.assessor.assess(c, TransitionSpeed.ACCELERATED)
        gradual = self.assessor.assess(c, TransitionSpeed.GRADUAL)
        vuln_order = [VulnerabilityLevel.LOW, VulnerabilityLevel.MEDIUM, VulnerabilityLevel.HIGH, VulnerabilityLevel.CRITICAL]
        assert vuln_order.index(accel.vulnerability) >= vuln_order.index(gradual.vulnerability)

    def test_key_risks_populated(self):
        c = make_community()
        impact = self.assessor.assess(c, TransitionSpeed.ACCELERATED)
        assert len(impact.key_risks) >= 1

    def test_recommendations_populated(self):
        c = make_community()
        impact = self.assessor.assess(c, TransitionSpeed.MODERATE)
        assert len(impact.recommendations) >= 1

    def test_compare_scenarios_returns_all_three(self):
        c = make_community()
        results = self.assessor.compare_scenarios(c)
        assert set(results.keys()) == set(TransitionSpeed)

    def test_portfolio_summary(self):
        communities = [make_community(community_id=f"C{i}") for i in range(3)]
        summary = self.assessor.portfolio_vulnerability_summary(communities, TransitionSpeed.MODERATE)
        assert summary["total_communities"] == 3
        assert summary["total_direct_jobs_at_risk"] == 12_500 * 3

    def test_portfolio_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.assessor.portfolio_vulnerability_summary([], TransitionSpeed.GRADUAL)

    def test_invalid_community_type_raises(self):
        with pytest.raises(TypeError):
            self.assessor.assess({"community_id": "bad"}, TransitionSpeed.GRADUAL)
