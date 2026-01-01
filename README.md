# Energy Transition Planner

Energy transition scenario planning and financial modeling tools for coal companies

## Features
- Data ingestion from CSV/Excel input files
- Automated analysis and KPI calculation
- Summary statistics and trend reporting
- Sample data generator for testing and development

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from src.main import EnergyTransitionPlanner

analyzer = EnergyTransitionPlanner()
df = analyzer.load_data("data/sample.csv")
result = analyzer.analyze(df)
print(result)
```

## Data Format

Expected CSV columns: `year, scenario, coal_production_mt, revenue_usd_m, capex_renewable_usd_m, carbon_cost_usd_m, npv_usd_m`

## Project Structure

```
energy-transition-planner/
├── src/
│   ├── main.py          # Core analysis logic
│   └── data_generator.py # Sample data generator
├── data/                # Data directory (gitignored for real data)
├── examples/            # Usage examples
├── requirements.txt
└── README.md
```

## License

MIT License — free to use, modify, and distribute.


## Usage Examples

### Stranded Asset Risk Assessment

```python
from src.main import EnergyTransitionPlanner

planner = EnergyTransitionPlanner()

risk = planner.calculate_stranded_asset_risk(
    asset_book_value_usd=500_000_000,   # $500M coal plant
    remaining_life_years=25,
    coal_demand_decline_pct_annual=4.0,
    carbon_price_usd_per_tco2=50.0,
    annual_emissions_tco2=800_000,
)

print(f"Risk score:        {risk['risk_score']:.1f}/100")
print(f"Urgency:           {risk['transition_urgency']}")
print(f"Stranding year:    {risk['stranding_year']}")
print(f"Stranded value:   ${risk['stranded_value_usd']:,.0f}")
print(f"Carbon liability: ${risk['carbon_liability_npv_usd']:,.0f}")
# Risk score:        65.0/100
# Urgency:           high
# Stranding year:    13
```

Refer to the `tests/` directory for comprehensive example implementations.
