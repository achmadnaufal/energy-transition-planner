"""
Unit tests for stranded asset risk calculation.
"""
import pytest
from src.main import EnergyTransitionPlanner


@pytest.fixture
def planner():
    return EnergyTransitionPlanner()


class TestStrandedAssetRisk:

    def test_high_decline_rate_strands_early(self, planner):
        """Fast coal demand decline → asset strands early."""
        result = planner.calculate_stranded_asset_risk(
            asset_book_value_usd=500_000_000,
            remaining_life_years=30,
            coal_demand_decline_pct_annual=10.0,
        )
        assert result["stranding_year"] is not None
        assert result["stranding_year"] < 20

    def test_low_decline_no_early_stranding(self, planner):
        """Very low decline rate → no stranding within asset life."""
        result = planner.calculate_stranded_asset_risk(
            asset_book_value_usd=100_000_000,
            remaining_life_years=10,
            coal_demand_decline_pct_annual=1.0,
        )
        # At 1% annual decline over 10 years, won't hit 30% stranding threshold
        assert result["stranding_year"] is None

    def test_carbon_liability_zero_without_emissions(self, planner):
        result = planner.calculate_stranded_asset_risk(
            asset_book_value_usd=200_000_000,
            remaining_life_years=15,
            annual_emissions_tco2=0,
        )
        assert result["carbon_liability_npv_usd"] == 0.0

    def test_carbon_liability_positive_with_emissions(self, planner):
        result = planner.calculate_stranded_asset_risk(
            asset_book_value_usd=200_000_000,
            remaining_life_years=15,
            carbon_price_usd_per_tco2=50.0,
            annual_emissions_tco2=100_000,
        )
        assert result["carbon_liability_npv_usd"] > 0

    def test_invalid_book_value_raises(self, planner):
        with pytest.raises(ValueError, match="asset_book_value_usd must be positive"):
            planner.calculate_stranded_asset_risk(
                asset_book_value_usd=0, remaining_life_years=10
            )

    def test_invalid_remaining_life_raises(self, planner):
        with pytest.raises(ValueError, match="remaining_life_years must be at least 1"):
            planner.calculate_stranded_asset_risk(
                asset_book_value_usd=100_000_000, remaining_life_years=0
            )

    def test_risk_score_0_to_100(self, planner):
        result = planner.calculate_stranded_asset_risk(
            asset_book_value_usd=500_000_000,
            remaining_life_years=25,
            coal_demand_decline_pct_annual=5.0,
        )
        assert 0 <= result["risk_score"] <= 100

    def test_urgency_bands(self, planner):
        critical = planner.calculate_stranded_asset_risk(
            asset_book_value_usd=500_000_000,
            remaining_life_years=30,
            coal_demand_decline_pct_annual=8.0,
            carbon_price_usd_per_tco2=80.0,
            annual_emissions_tco2=200_000,
        )
        assert critical["transition_urgency"] in ("critical", "high")

        low = planner.calculate_stranded_asset_risk(
            asset_book_value_usd=100_000_000,
            remaining_life_years=5,
            coal_demand_decline_pct_annual=0.5,
        )
        assert low["transition_urgency"] in ("low", "moderate")
