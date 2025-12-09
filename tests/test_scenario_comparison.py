"""
Unit tests for scenario comparison functionality in EnergyTransitionPlanner.

Tests cover:
- Scenario comparison calculations (coal reduction, renewable growth, NPV)
- Financial metrics (capex efficiency, NPV/capex ratio)
- Workforce transition analysis
- Edge cases (empty scenarios, missing fields)
"""

import pytest
import pandas as pd
from src.main import EnergyTransitionPlanner


@pytest.fixture
def planner():
    """Fixture: EnergyTransitionPlanner instance."""
    return EnergyTransitionPlanner()


@pytest.fixture
def sample_scenarios():
    """Fixture: Sample transition scenarios."""
    return {
        "conservative": {
            "scenario_id": "conservative",
            "scenario_name": "Conservative Transition",
            "coal_capacity_2026_mw": 5000,
            "coal_capacity_2035_mw": 3000,
            "renewables_capacity_2026_mw": 500,
            "renewables_capacity_2035_mw": 2500,
            "capex_billion_usd": 2.5,
            "workers_transitioned": 2000,
            "npv_billion_usd": 1.2,
            "timeline_years": 10,
        },
        "aggressive": {
            "scenario_id": "aggressive",
            "scenario_name": "Aggressive Transition",
            "coal_capacity_2026_mw": 5000,
            "coal_capacity_2035_mw": 500,
            "renewables_capacity_2026_mw": 500,
            "renewables_capacity_2035_mw": 4500,
            "capex_billion_usd": 6.5,
            "workers_transitioned": 4500,
            "npv_billion_usd": 3.5,
            "timeline_years": 10,
        },
    }


class TestScenarioComparison:
    """Test suite for scenario comparison functionality."""

    def test_compare_scenarios_happy_path(self, planner, sample_scenarios):
        """Test scenario comparison with valid data."""
        result = planner.compare_scenarios(sample_scenarios)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # Two scenarios
        assert "scenario_id" in result.columns
        assert "coal_capacity_reduction_pct" in result.columns
        assert "npv_capex_ratio" in result.columns

    def test_compare_scenarios_empty_dict_raises_error(self, planner):
        """Test that empty scenarios dict raises ValueError."""
        with pytest.raises(ValueError, match="scenarios dict cannot be empty"):
            planner.compare_scenarios({})

    def test_compare_scenarios_coal_reduction_calculation(self, planner, sample_scenarios):
        """Test coal capacity reduction percentage calculation."""
        result = planner.compare_scenarios(sample_scenarios)
        
        # Conservative: (5000 - 3000) / 5000 * 100 = 40%
        conservative_row = result[result["scenario_id"] == "conservative"].iloc[0]
        assert conservative_row["coal_capacity_reduction_pct"] == pytest.approx(40.0, rel=0.01)
        
        # Aggressive: (5000 - 500) / 5000 * 100 = 90%
        aggressive_row = result[result["scenario_id"] == "aggressive"].iloc[0]
        assert aggressive_row["coal_capacity_reduction_pct"] == pytest.approx(90.0, rel=0.01)

    def test_compare_scenarios_renewable_growth(self, planner, sample_scenarios):
        """Test renewable energy capacity growth calculation."""
        result = planner.compare_scenarios(sample_scenarios)
        
        conservative_row = result[result["scenario_id"] == "conservative"].iloc[0]
        # 2500 - 500 = 2000 MW growth
        assert conservative_row["renewables_growth_mw"] == pytest.approx(2000, rel=0.01)

    def test_compare_scenarios_npv_capex_ratio(self, planner, sample_scenarios):
        """Test NPV/CAPEX ratio calculation."""
        result = planner.compare_scenarios(sample_scenarios)
        
        conservative_row = result[result["scenario_id"] == "conservative"].iloc[0]
        # 1.2 / 2.5 = 0.48
        assert conservative_row["npv_capex_ratio"] == pytest.approx(0.48, rel=0.01)
        
        aggressive_row = result[result["scenario_id"] == "aggressive"].iloc[0]
        # 3.5 / 6.5 ≈ 0.54
        assert aggressive_row["npv_capex_ratio"] == pytest.approx(0.54, rel=0.01)

    def test_compare_scenarios_worker_transition_rate(self, planner, sample_scenarios):
        """Test workforce transition rate calculation."""
        result = planner.compare_scenarios(sample_scenarios)
        
        conservative_row = result[result["scenario_id"] == "conservative"].iloc[0]
        # 2000 / 15000 * 100 ≈ 13.3%
        assert conservative_row["worker_transition_rate_pct"] == pytest.approx(13.3, rel=0.1)

    def test_compare_scenarios_missing_fields_ignored(self, planner):
        """Test that scenarios with missing required fields are skipped."""
        scenarios = {
            "complete": {
                "scenario_id": "complete",
                "coal_capacity_2026_mw": 5000,
                "coal_capacity_2035_mw": 3000,
                "renewables_capacity_2026_mw": 500,
                "renewables_capacity_2035_mw": 2500,
                "capex_billion_usd": 2.5,
                "workers_transitioned": 2000,
            },
            "incomplete": {
                "scenario_id": "incomplete",
                "coal_capacity_2026_mw": 5000,
                # Missing other required fields
            },
        }
        
        result = planner.compare_scenarios(scenarios)
        
        # Only the complete scenario should be included
        assert len(result) == 1
        assert result.iloc[0]["scenario_id"] == "complete"

    def test_compare_scenarios_column_presence(self, planner, sample_scenarios):
        """Test that all expected columns are present."""
        result = planner.compare_scenarios(sample_scenarios)
        
        expected_columns = [
            "scenario_id",
            "scenario_name",
            "coal_capacity_reduction_pct",
            "renewables_growth_mw",
            "total_transition_capex_billion_usd",
            "npv_billion_usd",
            "npv_capex_ratio",
            "workers_transitioned",
            "worker_transition_rate_pct",
            "timeline_years",
        ]
        
        for col in expected_columns:
            assert col in result.columns, f"Column '{col}' missing from comparison result"

    def test_compare_scenarios_aggressive_vs_conservative(self, planner, sample_scenarios):
        """Test that aggressive scenario shows better financial returns."""
        result = planner.compare_scenarios(sample_scenarios)
        
        conservative = result[result["scenario_id"] == "conservative"].iloc[0]
        aggressive = result[result["scenario_id"] == "aggressive"].iloc[0]
        
        # Aggressive should have higher NPV and coal reduction
        assert aggressive["npv_billion_usd"] > conservative["npv_billion_usd"]
        assert aggressive["coal_capacity_reduction_pct"] > conservative["coal_capacity_reduction_pct"]
