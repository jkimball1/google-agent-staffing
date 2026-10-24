"""Member 2 — Staffing simulation.

Owner: TBD
Branch: feature/simulation

Simulates day by day, summarizes by month. Rules (see docs/assumptions.md):
  - all agents start 2026 with no advertisers assigned
  - each productive agent supports at most 10 advertisers at a time
  - each advertiser is supported for 60 days, then frees the slot
  - unassigned advertisers wait up to 60 days, then expire (no uplift)
  - hires take one month of training before becoming productive
  - terminations need one month of notice; cost 40% of annual salary
"""

import pandas as pd

from src.schemas import RESULTS_COLUMNS

AGENT_CAPACITY = 10
SUPPORT_DAYS = 60
MAX_WAIT_DAYS = 60
TERMINATION_COST_RATE = 0.40


def simulate_plan(
    demand_df: pd.DataFrame,
    staffing_plan_df: pd.DataFrame,
    country_parameters_df: pd.DataFrame,
) -> pd.DataFrame:
    """Run a staffing plan against demand.

    Inputs follow DEMAND_COLUMNS, STAFFING_PLAN_COLUMNS, COUNTRY_PARAMETERS_COLUMNS.
    Returns one row per country-month with RESULTS_COLUMNS.
    """
    raise NotImplementedError
