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
