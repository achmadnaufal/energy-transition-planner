"""Unit tests for RenewableCapacityOptimizer."""

import pytest
from src.renewable_capacity_optimizer import (
    RenewableCapacityOptimizer,
    CoalAsset,
    RenewableType,
    TransitionPlan,
    TECH_PARAMS,
)


@pytest.fixture
def optimizer():
    return RenewableCapacityOptimizer(base_year=2025)


@pytest.fixture
def coal_asset():
    return CoalAsset(
        asset_id="PLT-001",
        name="Suralaya Unit 1",
        coal_capacity_mw=400,
        annual_generation_gwh=2_800,
        retirement_year=2032,
        coal_lcoe_usd_per_mwh=65.0,
    )


@pytest.fixture
def simple_mix():
    return {RenewableType.SOLAR_PV: 60.0, RenewableType.GEOTHERMAL: 40.0}


class TestCoalAsset:
    def test_invalid_capacity(self):
        with pytest.raises(ValueError, match="coal_capacity_mw"):
            CoalAsset("X", "X", -100, 2800, 2030, 65.0)

    def test_invalid_lcoe(self):
        with pytest.raises(ValueError, match="coal_lcoe_usd_per_mwh"):
            CoalAsset("X", "X", 400, 2800, 2030, -10.0)

    def test_valid_asset(self, coal_asset):
        assert coal_asset.coal_capacity_mw == 400


class TestRenewableCapacityOptimizer:
    def test_basic_plan_generated(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        assert isinstance(plan, TransitionPlan)
        assert plan.total_renewable_capacity_mw > 0

    def test_capacity_above_coal_with_buffer(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        # With 20% buffer, total MW should be 400 * 1.2 = 480
        assert plan.total_renewable_capacity_mw == pytest.approx(480.0, rel=1e-4)

    def test_total_capex_positive(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        assert plan.total_capex_usd > 0

    def test_weighted_lcoe_in_range(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        min_lcoe = min(TECH_PARAMS[t]["lcoe_usd_per_mwh"] for t in simple_mix)
        max_lcoe = max(TECH_PARAMS[t]["lcoe_usd_per_mwh"] for t in simple_mix)
        assert min_lcoe <= plan.weighted_avg_lcoe_usd_per_mwh <= max_lcoe

    def test_lcoe_delta_calculated(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        assert plan.lcoe_delta_vs_coal == pytest.approx(
            plan.weighted_avg_lcoe_usd_per_mwh - coal_asset.coal_lcoe_usd_per_mwh,
            rel=1e-4
        )

    def test_mix_must_sum_to_100(self, optimizer, coal_asset):
        bad_mix = {RenewableType.SOLAR_PV: 60.0, RenewableType.WIND_ONSHORE: 20.0}
        with pytest.raises(ValueError, match="100%"):
            optimizer.optimize(coal_asset, bad_mix)

    def test_empty_mix_raises(self, optimizer, coal_asset):
        with pytest.raises(ValueError, match="empty"):
            optimizer.optimize(coal_asset, {})

    def test_negative_allocation_raises(self, optimizer, coal_asset):
        with pytest.raises(ValueError, match="negative"):
            optimizer.optimize(coal_asset, {RenewableType.SOLAR_PV: 110.0, RenewableType.GEOTHERMAL: -10.0})

    def test_milestones_present(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        assert len(plan.milestones) >= 1
        assert "completion_year" in plan.milestones[0]

    def test_grid_stability_solar_heavy_warns(self, optimizer, coal_asset):
        solar_heavy = {RenewableType.SOLAR_PV: 90.0, RenewableType.WIND_ONSHORE: 10.0}
        plan = optimizer.optimize(coal_asset, solar_heavy)
        # Solar-heavy mix should trigger low stability warning
        assert any("STABILITY" in w.upper() for w in plan.warnings)

    def test_timeline_risk_warning(self):
        optimizer_early = RenewableCapacityOptimizer(base_year=2028)
        asset = CoalAsset("X", "X", 400, 2800, 2029, 65.0)
        mix = {RenewableType.GEOTHERMAL: 100.0}  # 5 year construction
        plan = optimizer_early.optimize(asset, mix)
        assert any("TIMELINE" in w.upper() for w in plan.warnings)

    def test_to_dict_structure(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        d = plan.to_dict()
        assert "total_capex_usd" in d
        assert "mix_breakdown" in d
        assert "milestones" in d
        assert "grid_stability_index" in d

    def test_compare_mixes_sorted_by_lcoe(self, optimizer, coal_asset):
        mixes = [
            {RenewableType.WIND_OFFSHORE: 100.0},  # expensive
            {RenewableType.SOLAR_PV: 100.0},        # cheaper
        ]
        plans = optimizer.compare_mixes(coal_asset, mixes)
        assert plans[0].weighted_avg_lcoe_usd_per_mwh <= plans[1].weighted_avg_lcoe_usd_per_mwh

    def test_capacity_adequacy_ratio(self, optimizer, coal_asset, simple_mix):
        plan = optimizer.optimize(coal_asset, simple_mix)
        assert plan.capacity_adequacy_ratio > 0

    def test_no_buffer_option(self):
        optimizer_no_buf = RenewableCapacityOptimizer(capacity_buffer_pct=0, base_year=2025)
        asset = CoalAsset("X", "X", 400, 2800, 2032, 65.0)
        mix = {RenewableType.SOLAR_PV: 100.0}
        plan = optimizer_no_buf.optimize(asset, mix)
        assert plan.total_renewable_capacity_mw == pytest.approx(400.0, rel=1e-4)

    def test_invalid_buffer_raises(self):
        with pytest.raises(ValueError, match="capacity_buffer_pct"):
            RenewableCapacityOptimizer(capacity_buffer_pct=150)

    def test_hydro_high_stability(self, optimizer, coal_asset):
        hydro_mix = {RenewableType.HYDRO: 100.0}
        plan = optimizer.optimize(coal_asset, hydro_mix)
        assert plan.weighted_grid_stability_index == pytest.approx(0.90)
