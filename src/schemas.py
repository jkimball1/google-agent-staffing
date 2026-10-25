"""Shared data contracts between modules.

This file is the single source of truth for the column names in INTERFACES.md.
If you need to change a contract, change it here AND in INTERFACES.md in the
same pull request, and tag the owners of the modules that consume it.
"""

import pandas as pd

# Forecasting -> Simulation / Optimization
# One row per country per calendar day of 2026.
DEMAND_COLUMNS = [
    "country",                 # str, matches country_parameters.country
    "date",                    # YYYY-MM-DD, 2026-01-01 .. 2026-12-31
    "eligible_signups",        # float >= 0, expected eligible advertiser arrivals that day
    "mean_annual_budget_usd",  # float >= 0, mean annual ad budget of those arrivals
]

# Workbook-derived constants per country (salary, eligibility, starting staff).
COUNTRY_PARAMETERS_COLUMNS = [
    "country",
    "annual_salary_usd",           # per agent
    "eligibility_threshold_usd",   # minimum annual budget to qualify for support
    "agents_jan_2026",             # starting headcount
]

# Optimization -> Simulation (a candidate plan to evaluate).
# One row per country per month. Decisions are made at the start of the month.
STAFFING_PLAN_COLUMNS = [
    "country",
    "month",                   # YYYY-MM, 2026-01 .. 2026-12
    "hires_requested",         # int >= 0, become productive the following month
    "terminations_requested",  # int >= 0, notice given this month, leave the following month
]

# Simulation / Optimization -> GenAI, notebook, outputs/plan_2026.csv
# One row per country per month: 22 countries x 12 months = 264 rows.
RESULTS_COLUMNS = [
    "country",
    "month",
    "forecast_eligible",        # eligible arrivals that month
    "agents_active",            # productive agents incl. any serving notice (excludes trainees)
    "agents_in_training",
    "agents_hired",
    "agents_terminated",
    "advertisers_supported",    # new assignments started that month
    "advertisers_waiting",      # still unassigned at month end
    "advertisers_expired",      # waited > 60 days, lost
    "average_wait_days",
    "utilization",              # occupied slots / (agents_active * 10), 0..1
    "incremental_revenue_usd",
    "salary_cost_usd",
    "termination_cost_usd",
    "total_cost_usd",
    "net_value_usd",            # incremental_revenue_usd - total_cost_usd
]


def validate(df: pd.DataFrame, columns: list[str], name: str = "dataframe") -> pd.DataFrame:
    """Raise ValueError if `df` is missing any contract column. Returns df for chaining."""
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")
    return df
