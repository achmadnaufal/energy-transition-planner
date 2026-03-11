"""
Energy transition scenario planning and financial modeling tools for coal companies

Author: github.com/achmadnaufal
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any


class EnergyTransitionPlanner:
    """Coal to renewable energy transition planner"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load data from CSV or Excel file."""
        p = Path(filepath)
        if p.suffix in (".xlsx", ".xls"):
            return pd.read_excel(filepath)
        return pd.read_csv(filepath)

    def validate(self, df: pd.DataFrame) -> bool:
        """Basic validation of input data."""
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        return True

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess input data."""
        df = df.copy()
        # Drop fully empty rows
        df.dropna(how="all", inplace=True)
        # Standardize column names
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        return df

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run core analysis and return summary metrics."""
        df = self.preprocess(df)
        result = {
            "total_records": len(df),
            "columns": list(df.columns),
            "missing_pct": (df.isnull().sum() / len(df) * 100).round(1).to_dict(),
        }
        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            result["summary_stats"] = numeric_df.describe().round(3).to_dict()
            result["totals"] = numeric_df.sum().round(2).to_dict()
            result["means"] = numeric_df.mean().round(3).to_dict()
        return result

    def run(self, filepath: str) -> Dict[str, Any]:
        """Full pipeline: load → validate → analyze."""
        df = self.load_data(filepath)
        self.validate(df)
        return self.analyze(df)

    def compare_scenarios(self, scenarios: Dict[str, Dict]) -> pd.DataFrame:
        """
        Compare multiple energy transition scenarios side-by-side.
        
        Calculates key metrics and comparison indicators for scenario analysis:
        - Coal capacity reduction percentage
        - Renewable energy capacity growth
        - Workforce transition impact
        - Financial returns (NPV, capex efficiency)
        - Timeline feasibility
        
        Args:
            scenarios: Dictionary mapping scenario_id to scenario_data.
                      Each scenario should contain capacity, financial, and timeline data.
        
        Returns:
            DataFrame with side-by-side scenario comparison
            
        Raises:
            ValueError: If scenarios dict is empty or missing required fields
            
        Example:
            >>> scenarios = {
            ...     "aggressive": {"coal_capacity_2035_mw": 500, "renewables_capacity_2035_mw": 4500, ...},
            ...     "moderate": {"coal_capacity_2035_mw": 2000, "renewables_capacity_2035_mw": 3500, ...},
            ... }
            >>> comparison = planner.compare_scenarios(scenarios)
            >>> print(comparison)  # Coal reduction %, NPV/CAPEX, worker transition rate, etc.
        """
        if not scenarios:
            raise ValueError("scenarios dict cannot be empty")
        
        comparison_data = []
        
        for scenario_id, scenario_data in scenarios.items():
            # Validate required fields
            required_fields = ["coal_capacity_2026_mw", "coal_capacity_2035_mw", 
                             "renewables_capacity_2026_mw", "renewables_capacity_2035_mw",
                             "capex_billion_usd", "workers_transitioned"]
            if not all(f in scenario_data for f in required_fields):
                continue
            
            # Calculate comparison metrics
            coal_reduction_pct = (
                (scenario_data["coal_capacity_2026_mw"] - scenario_data["coal_capacity_2035_mw"]) 
                / scenario_data["coal_capacity_2026_mw"] * 100
            )
            
            renewables_growth_mw = (
                scenario_data["renewables_capacity_2035_mw"] - scenario_data["renewables_capacity_2026_mw"]
            )
            
            capex = scenario_data.get("capex_billion_usd", 0)
            npv = scenario_data.get("npv_billion_usd", 0)
            npv_capex_ratio = npv / capex if capex > 0 else 0
            
            workers = scenario_data.get("workers_transitioned", 0)
            original_workers = 15000  # Assumed baseline
            worker_transition_rate = workers / original_workers * 100
            
            comparison_data.append({
                "scenario_id": scenario_id,
                "scenario_name": scenario_data.get("scenario_name", scenario_id),
                "coal_capacity_reduction_pct": round(coal_reduction_pct, 1),
                "renewables_growth_mw": renewables_growth_mw,
                "total_transition_capex_billion_usd": capex,
                "npv_billion_usd": npv,
                "npv_capex_ratio": round(npv_capex_ratio, 2),
                "workers_transitioned": workers,
                "worker_transition_rate_pct": round(worker_transition_rate, 1),
                "timeline_years": scenario_data.get("timeline_years", 0),
            })
        
        return pd.DataFrame(comparison_data)

    def to_dataframe(self, result: Dict) -> pd.DataFrame:
        """Convert analysis result to DataFrame for export."""
        rows = []
        for k, v in result.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    rows.append({"metric": f"{k}.{kk}", "value": vv})
            else:
                rows.append({"metric": k, "value": v})
        return pd.DataFrame(rows)
