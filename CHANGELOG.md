# Changelog

## [1.3.0] - 2026-03-23

### Added
- `src/stranded_asset_calculator.py` — DCF-based stranded asset risk calculator
  - `CoalAsset` dataclass with production, financials, and emissions attributes
  - `StrandedAssetCalculator` with IEA WEO 2023 carbon price trajectories (STEPS/APS/NZE)
  - `asset_npv()` — scenario-specific DCF valuation with carbon cost deduction
  - `stranded_value()` — per-asset write-down risk vs. book value
  - `stranded_value_report()` — portfolio-level stranded asset report
  - `expected_stranded_value()` — probability-weighted expected stranded value
  - Carbon price interpolation between IEA milestone years
- `data/sample_coal_assets.csv` — 6 Indonesian/PNG coal assets with financial profiles
- 30 unit tests in `tests/test_stranded_asset_calculator.py`

### References
- IEA World Energy Outlook 2023 (STEPS, APS, NZE)
- Carbon Tracker Initiative: Unburnable Carbon

## [1.2.0] - 2026-03-15

### Added
- **Stranded Asset Risk Calculator** — `calculate_stranded_asset_risk()`: Estimates financial exposure from early coal asset retirement using demand-decline modelling and carbon liability NPV; returns stranding year, risk score (0–100), and transition urgency band
- **Unit Tests** — 8 new tests in `tests/test_stranded_asset.py` covering decline scenarios, carbon liability, validation errors, and urgency bands
- **README** — Added stranded asset risk usage example with sample output

## [1.1.0] - 2026-03-11

### Added
- **Scenario Comparison Method** — New `compare_scenarios()` for side-by-side analysis:
  - Coal capacity reduction percentage tracking
  - Renewable energy growth calculations
  - Financial metrics (capex, NPV, NPV/capex ratio)
  - Workforce transition rate analysis
  - Multi-scenario cost-benefit comparison
- **Transition Scenarios Sample Data** — Created `sample_data/transition_scenarios.json`:
  - Conservative, moderate, and aggressive transition paths
  - Realistic Indonesian coal-to-renewable transition models (2026-2035)
  - Complete financial and operational parameters
- **Scenario Comparison Test Suite** — Added 10 comprehensive unit tests:
  - Happy path scenario comparison
  - Financial metrics validation
  - Workforce transition rate calculations
  - Edge case handling (missing fields, empty scenarios)
  - Scenario comparison rankings (aggressive vs. conservative)

### Changed
- Enhanced method docstrings with practical usage examples
- Improved error handling for scenario validation

## [2026-03-08]
- Enhanced documentation and examples
- Added unit test fixtures and test coverage
- Added comprehensive docstrings to key functions
- Added error handling for edge cases
- Improved README with setup and usage examples
