# Changelog

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
