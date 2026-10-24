"""Member 3 — Staffing optimization.

Owner: TBD
Branch: feature/optimization
"""

from typing import Callable

import pandas as pd


def optimize_staffing(
    demand_df: pd.DataFrame,
    country_parameters_df: pd.DataFrame,
    simulate_fn: Callable[[pd.DataFrame, pd.DataFrame, pd.DataFrame], pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Search candidate staffing plans and pick the one with the best net value.

    `simulate_fn` has the signature of src.simulation.simulator.simulate_plan,
    so this module can be developed against a stand-in before the real one exists.

    Returns (recommended_plan_df, evaluated_results_df):
      recommended_plan_df  -> STAFFING_PLAN_COLUMNS
      evaluated_results_df -> RESULTS_COLUMNS (this becomes outputs/plan_2026.csv)
    """
    raise NotImplementedError
