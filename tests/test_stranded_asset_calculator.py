"""Unit tests for StrandedAssetCalculator (new Scope 3 + DCF-based approach)."""
import pytest
from src.stranded_asset_calculator import (
    CoalAsset, StrandedAssetCalculator, CARBON_PRICE_PATHS, SCENARIO_WEIGHTS
)


@pytest.fixture
def asset_a():
    return CoalAsset(
        asset_id="MN-KAL-001",
        asset_name="Kalimantan South Mine",
        reserve_mt=250.0,
        annual_production_mt=8.0,
        mine_life_years=30,
        book_value_usd_m=420.0,
        annual_revenue_usd_m=160.0,
        annual_opex_usd_m=105.0,
        scope1_intensity_tCO2e_per_t=0.032,
    )


@pytest.fixture
def asset_b():
    return CoalAsset(
        asset_id="MN-SUM-002",
        asset_name="South Sumatra Mine",
        reserve_mt=80.0,
        annual_production_mt=3.5,
        mine_life_years=22,
        book_value_usd_m=180.0,
        annual_revenue_usd_m=65.0,
        annual_opex_usd_m=48.0,
        scope1_intensity_tCO2e_per_t=0.041,
    )


@pytest.fixture
def calc(asset_a, asset_b):
    c = StrandedAssetCalculator(discount_rate=0.10)
    c.add_asset(asset_a)
    c.add_asset(asset_b)
    return c


# --- CoalAsset validation ---

def test_invalid_reserve():
    with pytest.raises(ValueError, match="reserve_mt"):
        CoalAsset("x", "Mine", -10, 2, 10, 100, 50, 30)

def test_invalid_production():
    with pytest.raises(ValueError, match="annual_production_mt"):
        CoalAsset("x", "Mine", 100, 0, 10, 100, 50, 30)

def test_invalid_mine_life():
    with pytest.raises(ValueError, match="mine_life_years"):
        CoalAsset("x", "Mine", 100, 2, 0, 100, 50, 30)

def test_invalid_book_value():
    with pytest.raises(ValueError, match="book_value_usd_m"):
        CoalAsset("x", "Mine", 100, 2, 10, -1, 50, 30)

def test_invalid_intensity():
    with pytest.raises(ValueError, match="scope1_intensity"):
        CoalAsset("x", "Mine", 100, 2, 10, 100, 50, 30, scope1_intensity_tCO2e_per_t=-0.1)

def test_annual_ebitda(asset_a):
    assert asset_a.annual_ebitda_usd_m == 55.0  # 160 - 105

def test_annual_emissions(asset_a):
    # 8e6 * 0.032 = 256,000 tCO2e
    assert asset_a.annual_emissions_tCO2e == 256_000.0


# --- Calculator management ---

def test_add_asset(calc):
    assert len(calc) == 2

def test_add_duplicate_raises(calc, asset_a):
    with pytest.raises(ValueError, match="already registered"):
        calc.add_asset(asset_a)

def test_remove_asset(calc):
    removed = calc.remove_asset("MN-KAL-001")
    assert removed is True
    assert len(calc) == 1

def test_remove_nonexistent(calc):
    assert calc.remove_asset("UNKNOWN") is False

def test_invalid_discount_rate():
    with pytest.raises(ValueError, match="discount_rate"):
        StrandedAssetCalculator(discount_rate=1.5)

def test_repr(calc):
    assert "StrandedAssetCalculator" in repr(calc)


# --- Carbon price interpolation ---

def test_carbon_price_nze_2050(calc):
    price = calc._carbon_price_for_year("NZE", 2050)
    assert price == 250.0

def test_carbon_price_steps_below_start(calc):
    # Before 2026 → returns 2026 price
    price = calc._carbon_price_for_year("STEPS", 2020)
    assert price == CARBON_PRICE_PATHS["STEPS"][2026]

def test_carbon_price_interpolation(calc):
    # Between 2026 ($15) and 2030 ($25) for STEPS
    price = calc._carbon_price_for_year("STEPS", 2028)
    assert 15 < price < 25

def test_invalid_scenario(calc):
    with pytest.raises(ValueError, match="scenario"):
        calc._carbon_price_for_year("BAD_SCENARIO", 2030)


# --- NPV ---

def test_npv_steps_higher_than_nze(calc, asset_a):
    # Lower carbon price under STEPS → higher NPV
    npv_steps = calc.asset_npv(asset_a, "STEPS")
    npv_nze = calc.asset_npv(asset_a, "NZE")
    assert npv_steps > npv_nze

def test_npv_positive_under_steps(calc, asset_a):
    # Profitable mine with low carbon price should have positive NPV
    npv = calc.asset_npv(asset_a, "STEPS")
    assert npv > 0

def test_npv_decreases_with_high_carbon_price(calc, asset_a):
    npv_aps = calc.asset_npv(asset_a, "APS")
    npv_nze = calc.asset_npv(asset_a, "NZE")
    assert npv_aps > npv_nze


# --- Stranded value ---

def test_stranded_value_nze_positive(calc, asset_a):
    result = calc.stranded_value(asset_a, "NZE")
    # Under NZE, high carbon costs should strand significant value
    assert result["stranded_value_usd_m"] > 0
    assert result["at_risk"] is True

def test_stranded_value_keys(calc, asset_a):
    result = calc.stranded_value(asset_a, "STEPS")
    for key in ["asset_id", "book_value_usd_m", "npv_usd_m",
                "stranded_value_usd_m", "stranded_pct_of_book", "at_risk"]:
        assert key in result

def test_stranded_pct_of_book(calc, asset_a):
    result = calc.stranded_value(asset_a, "NZE")
    expected = round(result["stranded_value_usd_m"] / asset_a.book_value_usd_m * 100, 1)
    assert result["stranded_pct_of_book"] == expected


# --- Portfolio report ---

def test_report_empty():
    c = StrandedAssetCalculator()
    report = c.stranded_value_report("NZE")
    assert report["total_stranded_usd_m"] == 0.0

def test_report_keys(calc):
    report = calc.stranded_value_report("APS")
    for key in ["scenario", "total_book_value_usd_m", "total_npv_usd_m",
                "total_stranded_usd_m", "stranded_pct_of_portfolio",
                "assets_at_risk", "by_asset"]:
        assert key in report

def test_report_n_assets(calc):
    report = calc.stranded_value_report("NZE")
    assert report["n_assets"] == 2

def test_nze_more_stranded_than_steps(calc):
    r_steps = calc.stranded_value_report("STEPS")
    r_nze = calc.stranded_value_report("NZE")
    assert r_nze["total_stranded_usd_m"] > r_steps["total_stranded_usd_m"]


# --- Expected stranded value ---

def test_expected_stranded_keys(calc):
    result = calc.expected_stranded_value()
    assert "expected_stranded_usd_m" in result
    assert "by_scenario" in result

def test_expected_stranded_weighted(calc):
    result = calc.expected_stranded_value()
    by_scenario = result["by_scenario"]
    # Check weights sum to 1
    total_weight = sum(s["weight"] for s in by_scenario.values())
    assert abs(total_weight - 1.0) < 0.01

def test_scenario_weights_sum():
    assert abs(sum(SCENARIO_WEIGHTS.values()) - 1.0) < 0.01
